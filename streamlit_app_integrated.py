"""
OptiClaimAI - Fully Integrated Claims Processing
✅ PDF Upload + Form Filling + Real-Time Validation + AI Chat with Context
"""

import streamlit as st
import requests
from config import Config
from datetime import datetime, date
import json
import sys
from pathlib import Path
from typing import Dict, Optional, Any, List

# Add services to path
sys.path.insert(0, str(Path(__file__).parent))

# Import backend services
try:
    from services.pdf_parser import PDFClaimParser
    from services.validation_engine import ValidationEngine, ValidationSeverity
    from services.ai_engine import AIEngine
    from services.npi_lookup import get_npi_service
    from services.edi_bridge import get_edi_service
    from model.canonical_claim import CanonicalClaim, Patient, Provider, ServiceLine, Diagnosis, ClaimMetadata
    from engine.parser import EDI837Parser
except ImportError as e:
    st.error(f"❌ Failed to import services: {str(e)}")
    st.stop()

# ============= PAGE CONFIG =============

st.set_page_config(
    page_title="OptiClaimAI - Integrated",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============= CSS STYLING =============

st.markdown("""
<style>
    .header-section { text-align: center; padding: 20px 0; }
    .form-section { background-color: #f9f9f9; padding: 20px; border-radius: 8px; border: 1px solid #e0e0e0; }
    .chat-section { background-color: #ffffff; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0; }
    .chat-message { margin: 8px 0; padding: 10px; border-radius: 6px; }
    .chat-user { background-color: #e3f2fd; text-align: right; margin-left: 15%; }
    .chat-ai { background-color: #f5f5f5; margin-right: 5%; }
    .alert-high { background-color: #ffebee; border-left: 4px solid #f44336; padding: 10px; margin: 5px 0; border-radius: 4px; }
    .alert-medium { background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 10px; margin: 5px 0; border-radius: 4px; }
    .alert-low { background-color: #e8f5e9; border-left: 4px solid #4caf50; padding: 10px; margin: 5px 0; border-radius: 4px; }
    .success-box { background-color: #d4edda; border-left: 4px solid #28a745; padding: 10px; border-radius: 4px; margin: 10px 0; }
    .auto-fill-indicator { color: #4caf50; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ============= HELPER FUNCTIONS =============

def get_available_models() -> List[str]:
    """Get list of available Ollama models"""
    try:
        response = requests.get(f"{Config.OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return [m["name"] for m in models]
        return []
    except Exception:
        return []

def send_to_ollama(prompt: str, model: Optional[str] = None) -> str:
    """Send prompt to Ollama with error handling"""
    try:
        available_models = get_available_models()
        if not available_models:
            return "❌ No Ollama models available. Run: `ollama pull llama2`"
        
        selected_model = model or available_models[0]
        response = requests.post(
            f"{Config.OLLAMA_URL}/api/generate",
            json={"model": selected_model, "prompt": prompt, "stream": False},
            timeout=Config.OLLAMA_TIMEOUT
        )
        if response.status_code == 200:
            result = response.json().get("response", "")
            return result if result else "No response from AI"
        return f"❌ AI service error (status {response.status_code})"
    except requests.exceptions.Timeout:
        return "❌ AI timeout - model loading. Try again."
    except requests.exceptions.ConnectionError:
        return f"❌ Cannot connect to Ollama at {Config.OLLAMA_URL}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def validate_claim_data(claim_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate claim and return validation result"""
    try:
        engine = ValidationEngine()
        result = engine.validate_claim(claim_dict)
        return result.to_dict()
    except Exception as e:
        st.error(f"Validation error: {str(e)}")
        return None

def display_validation_result(result: Dict[str, Any]) -> None:
    """Display validation results in a formatted way"""
    if not result:
        return
    
    # Summary
    is_valid = result.get("is_valid", False)
    denial_risk = result.get("denial_risk_level", "UNKNOWN")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        status_color = "🟢" if is_valid else "🔴"
        st.metric("Status", f"{status_color} {'Valid' if is_valid else 'Invalid'}")
    with col2:
        st.metric("Denial Risk", denial_risk)
    with col3:
        st.metric("Risk Score", f"{result.get('denial_risk_score', 0):.0f}%")
    
    # Issues
    issues = result.get("issues", [])
    if issues:
        st.subheader("Issues Found")
        for issue in issues:
            severity = issue.get("severity", "LOW")
            css_class = {
                "HIGH": "alert-high",
                "MEDIUM": "alert-medium",
                "LOW": "alert-low"
            }.get(severity, "alert-low")
            
            st.markdown(f"""
<div class="{css_class}">
<strong>{severity}: {issue.get('field', 'Unknown')}</strong><br/>
{issue.get('issue', 'No details')}<br/>
<em>Fix: {issue.get('fix_hint', 'N/A')}</em>
</div>
""", unsafe_allow_html=True)

def get_ai_explanation(validation_result: Dict[str, Any]) -> str:
    """Get AI explanation of validation issues"""
    try:
        issues = validation_result.get("issues", [])
        if not issues:
            return "✅ No issues found! Your claim looks good."
        
        issues_text = "\n".join([
            f"- {issue.get('issue', 'Unknown')} (Severity: {issue.get('severity', 'UNKNOWN')})"
            for issue in issues
        ])
        
        prompt = f"""A healthcare claim has the following validation issues:

{issues_text}

Please explain in simple language:
1. What each issue means
2. Why it might cause claim denial
3. How to fix each issue

Be concise and practical."""
        
        models = get_available_models()
        if models:
            return send_to_ollama(prompt, models[0] if models else None)
        return "AI service unavailable"
    
    except Exception as e:
        return f"Error getting explanation: {str(e)}"

def save_claim_to_file(claim_dict: Dict[str, Any], filename: str = None) -> bool:
    """Save claim to JSON file"""
    try:
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"claim_{timestamp}.json"
        
        # Create claims directory if it doesn't exist
        claims_dir = Path("data/saved_claims")
        claims_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = claims_dir / filename
        with open(filepath, "w") as f:
            json.dump(claim_dict, f, indent=2, default=str)
        
        return True, str(filepath)
    except Exception as e:
        return False, str(e)

def lookup_npi(npi: str) -> Optional[Dict[str, Any]]:
    """Look up provider NPI"""
    try:
        npi_service = get_npi_service()
        result = npi_service.lookup_npi(npi)
        return result
    except Exception as e:
        st.error(f"NPI Lookup Error: {str(e)}")
        return None

def parse_edi_file(edi_content: str) -> Optional[Dict[str, Any]]:
    """Parse EDI 837P file"""
    try:
        edi_service = get_edi_service()
        parsed, error = edi_service.parse_edi_837p(edi_content)
        if error:
            st.warning(f"⚠️ EDI Parse Warning: {error}")
        return parsed
    except Exception as e:
        st.error(f"EDI Parse Error: {str(e)}")
        return None

def parse_free_text(text: str) -> Optional[Dict[str, Any]]:
    """Parse free-form text input (simplified regex-based)"""
    try:
        import re
        
        data = {
            "patient": {},
            "provider": {},
            "service_lines": [],
            "diagnoses": []
        }
        
        # Patient name pattern
        name_match = re.search(r'(?:Patient|For).*?(\w+)\s+(\w+)', text, re.IGNORECASE)
        if name_match:
            data["patient"]["first_name"] = name_match.group(1)
            data["patient"]["last_name"] = name_match.group(2)
        
        # DOB pattern
        dob_match = re.search(r'(?:DOB|Date of Birth).*?(\d{1,2})[/-](\d{1,2})[/-](\d{4})', text, re.IGNORECASE)
        if dob_match:
            data["patient"]["date_of_birth"] = f"{dob_match.group(3)}-{dob_match.group(1):0>2}-{dob_match.group(2):0>2}"
        
        # NPI pattern
        npi_match = re.search(r'(?:NPI|Provider.*?)(\d{10})', text, re.IGNORECASE)
        if npi_match:
            data["provider"]["npi"] = npi_match.group(1)
        
        # CPT code pattern
        cpt_match = re.search(r'(?:CPT|Code).*?(\d{5})', text, re.IGNORECASE)
        if cpt_match:
            data["service_lines"].append({"procedure_code": cpt_match.group(1)})
        
        # ICD-10 pattern
        icd_match = re.search(r'(?:ICD|Diagnosis).*?([A-Z]\d{2}(?:\.\d+)?)', text, re.IGNORECASE)
        if icd_match:
            data["diagnoses"].append({"icd10_code": icd_match.group(1)})
        
        return data if any([data["patient"], data["provider"]]) else None
    
    except Exception as e:
        st.error(f"Text Parse Error: {str(e)}")
        return None

# ============= SESSION STATE INITIALIZATION =============

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_view" not in st.session_state:
    st.session_state.current_view = "home"
if "current_claim" not in st.session_state:
    st.session_state.current_claim = {
        "patient": {},
        "provider": {},
        "service_lines": [],
        "diagnoses": []
    }
if "validation_result" not in st.session_state:
    st.session_state.validation_result = None
if "pdf_data" not in st.session_state:
    st.session_state.pdf_data = None
if "selected_model" not in st.session_state:
    models = get_available_models()
    st.session_state.selected_model = models[0] if models else None
if "npi_lookup_result" not in st.session_state:
    st.session_state.npi_lookup_result = None
if "saved_claims" not in st.session_state:
    st.session_state.saved_claims = []

# ============= MAIN LAYOUT =============

# HEADER
st.markdown("""<div class="header-section"><h1>🏥 OptiClaimAI</h1><p>Integrated Claims Processing with PDF Upload & AI</p></div>""", unsafe_allow_html=True)

ai_status = "🟢 Ready" if get_available_models() else "🔴 AI Offline"
st.caption(f"{ai_status} | {Config.OLLAMA_URL} | Models: {len(get_available_models())}")

st.divider()

# Main two-column layout
col_left, col_right = st.columns([1, 2])

# ============= LEFT COLUMN: CHAT =============

with col_left:
    st.markdown("### 💬 AI Assistant")
    
    # Model selector
    available_models = get_available_models()
    if available_models:
        st.session_state.selected_model = st.selectbox(
            "🤖 Model",
            available_models,
            index=available_models.index(st.session_state.selected_model) if st.session_state.selected_model in available_models else 0,
        )
    else:
        st.warning("⚠️ No Ollama models. Run: `ollama pull llama2`")
    
    st.divider()
    
    # Chat display
    with st.container(border=False):
        for msg in st.session_state.chat_history[-10:]:  # Show last 10 messages
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-message chat-user">👤 {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message chat-ai">🤖 {msg["content"]}</div>', unsafe_allow_html=True)
    
    st.divider()
    
    # Chat input
    user_input = st.text_input("Ask about claims...", placeholder="How do I fill the form?", key="chat_input")
    
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # Get AI response with context
        if st.session_state.current_claim.get("patient", {}).get("first_name"):
            context = f"(Filling claim for {st.session_state.current_claim['patient']['first_name']}): {user_input}"
        else:
            context = user_input
        
        ai_response = send_to_ollama(context, st.session_state.selected_model)
        st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
        st.rerun()
    
    # Quick action buttons
    st.divider()
    if st.button("🔄 Clear Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

# ============= RIGHT COLUMN: FORMS & CONTENT =============

with col_right:
    # HOME VIEW
    if st.session_state.current_view == "home":
        st.markdown("### 📝 Getting Started")
        
        st.write("""
**Choose how to submit your claim:**
1. **Upload PDF** - We'll extract data automatically
2. **Fill Form Manually** - Step-by-step guided form
3. **Free Text** - Natural language input
4. **EDI Upload** - Direct 837P file upload
        """)
        
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            if st.button("📁 Upload PDF", use_container_width=True, key="btn_pdf"):
                st.session_state.current_view = "upload_pdf"
                st.rerun()
        with col_b:
            if st.button("📋 Fill Form", use_container_width=True, key="btn_form"):
                st.session_state.current_view = "fill_form"
                st.rerun()
        with col_c:
            if st.button("📝 Free Text", use_container_width=True, key="btn_text"):
                st.session_state.current_view = "free_text"
                st.rerun()
        with col_d:
            if st.button("📤 EDI Upload", use_container_width=True, key="btn_edi"):
                st.session_state.current_view = "edi_upload"
                st.rerun()
        
        st.divider()
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ Validate", use_container_width=True, key="btn_validate"):
                st.session_state.current_view = "validate"
                st.rerun()
        with col_b:
            if st.button("⚙️ Settings", use_container_width=True, key="btn_settings"):
                st.session_state.current_view = "settings"
                st.rerun()
    
    # PDF UPLOAD VIEW
    elif st.session_state.current_view == "upload_pdf":
        st.markdown("### 📤 Upload Claim PDF")
        st.write("Upload a claim PDF and we'll automatically extract the data and fill your form.")
        
        uploaded_file = st.file_uploader("Select PDF file", type=["pdf"], label_visibility="collapsed")
        
        if uploaded_file:
            with st.spinner("📄 Parsing PDF..."):
                pdf_bytes = uploaded_file.read()
                pdf_data = PDFClaimParser.parse_from_pdf_bytes(pdf_bytes)
            
            if pdf_data:
                st.markdown('<div class="success-box">✅ PDF parsed! Auto-filled fields below:</div>', unsafe_allow_html=True)
                
                # Show extracted data
                st.json(pdf_data)
                
                # Populate claim with PDF data
                if st.button("✅ Use This Data", use_container_width=True):
                    st.session_state.pdf_data = pdf_data
                    # Pre-fill form view
                    st.session_state.current_view = "fill_form"
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"✅ PDF data extracted! {len([v for v in pdf_data.values() if v])} fields found. Now filling the form..."
                    })
                    st.rerun()
            else:
                st.warning("⚠️ Could not extract text from PDF. This might be a scanned image. Please fill the form manually.")
        
        if st.button("← Back", use_container_width=True):
            st.session_state.current_view = "home"
            st.rerun()
    
    # FILL FORM VIEW
    elif st.session_state.current_view == "fill_form":
        st.markdown("### 📋 Claim Details Form")
        st.write("Fill in the claim information. Fields marked **✅** were auto-filled from PDF.")
        
        with st.form("claim_form"):
            # Patient Section
            st.subheader("👤 Patient Information")
            col_a, col_b = st.columns(2)
            
            with col_a:
                pdf_marker = " ✅" if st.session_state.pdf_data and st.session_state.pdf_data.get("patient_first") else ""
                patient_first = st.text_input(
                    f"First Name *{pdf_marker}",
                    value=st.session_state.pdf_data.get("patient_first") if st.session_state.pdf_data else "",
                    placeholder="John"
                )
                patient_dob = st.date_input("Date of Birth *", value=None)
            
            with col_b:
                pdf_marker = " ✅" if st.session_state.pdf_data and st.session_state.pdf_data.get("patient_last") else ""
                patient_last = st.text_input(
                    f"Last Name *{pdf_marker}",
                    value=st.session_state.pdf_data.get("patient_last") if st.session_state.pdf_data else "",
                    placeholder="Doe"
                )
                pdf_marker = " ✅" if st.session_state.pdf_data and st.session_state.pdf_data.get("patient_member_id") else ""
                member_id = st.text_input(
                    f"Member ID *{pdf_marker}",
                    value=st.session_state.pdf_data.get("patient_member_id") if st.session_state.pdf_data else "",
                    placeholder="MEM123456"
                )
            
            # Provider Section
            st.subheader("👨‍⚕️ Provider Information")
            col_a, col_b = st.columns(2)
            
            with col_a:
                pdf_marker = " ✅" if st.session_state.pdf_data and st.session_state.pdf_data.get("provider_npi") else ""
                provider_npi = st.text_input(
                    f"NPI (10 digits) *{pdf_marker}",
                    value=st.session_state.pdf_data.get("provider_npi") if st.session_state.pdf_data else "",
                    placeholder="1234567890",
                    max_chars=10
                )
                
                # NPI Lookup Button
                if provider_npi and len(provider_npi) == 10 and st.button("🔍 Lookup NPI Details"):
                    npi_result = lookup_npi(provider_npi)
                    if npi_result:
                        st.session_state.npi_lookup_result = npi_result
                        st.success("✅ NPI Found!")
                
                pdf_marker = " ✅" if st.session_state.pdf_data and st.session_state.pdf_data.get("provider_first") else ""
                provider_first = st.text_input(
                    f"First Name{pdf_marker}",
                    value=st.session_state.npi_lookup_result.get("first_name", "") if st.session_state.npi_lookup_result else (st.session_state.pdf_data.get("provider_first") if st.session_state.pdf_data else ""),
                    placeholder="Jane"
                )
            
            with col_b:
                pdf_marker = " ✅" if st.session_state.pdf_data and st.session_state.pdf_data.get("provider_last") else ""
                provider_last = st.text_input(
                    f"Last Name{pdf_marker}",
                    value=st.session_state.npi_lookup_result.get("last_name", "") if st.session_state.npi_lookup_result else (st.session_state.pdf_data.get("provider_last") if st.session_state.pdf_data else ""),
                    placeholder="Smith"
                )
            
            # Service Section
            st.subheader("💊 Service Information")
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                service_date = st.date_input("Service Date *", value=datetime.now())
            with col_b:
                pdf_marker = " ✅" if st.session_state.pdf_data and st.session_state.pdf_data.get("procedure_code") else ""
                procedure_code = st.text_input(
                    f"CPT Code *{pdf_marker}",
                    value=st.session_state.pdf_data.get("procedure_code") if st.session_state.pdf_data else "",
                    placeholder="99213"
                )
            with col_c:
                pdf_marker = " ✅" if st.session_state.pdf_data and st.session_state.pdf_data.get("charge") else ""
                charge = st.number_input(
                    f"Charge ($) *{pdf_marker}",
                    min_value=0.0,
                    value=float(st.session_state.pdf_data.get("charge", 0)) if st.session_state.pdf_data else 0.0,
                    step=0.01
                )
            
            # Diagnosis Section
            st.subheader("🏷️ Diagnosis")
            col_a, col_b = st.columns(2)
            
            with col_a:
                pdf_marker = " ✅" if st.session_state.pdf_data and st.session_state.pdf_data.get("diagnosis_code") else ""
                diagnosis_code = st.text_input(
                    f"ICD-10 Code *{pdf_marker}",
                    value=st.session_state.pdf_data.get("diagnosis_code") if st.session_state.pdf_data else "",
                    placeholder="J45.901"
                )
            with col_b:
                diagnosis_desc = st.text_area("Description", placeholder="Optional diagnosis description")
            
            st.divider()
            
            # Submit button
            col_a, col_b = st.columns([1, 3])
            with col_a:
                submitted = st.form_submit_button("✅ Submit & Validate", use_container_width=True)
            with col_b:
                st.caption("* = Required fields")
            
            if submitted:
                # Build claim dictionary
                claim_dict = {
                    "patient": {
                        "first_name": patient_first,
                        "last_name": patient_last,
                        "date_of_birth": str(patient_dob) if patient_dob else None,
                        "member_id": member_id
                    },
                    "provider": {
                        "npi": provider_npi,
                        "first_name": provider_first,
                        "last_name": provider_last
                    },
                    "service_lines": [{
                        "service_date": str(service_date),
                        "procedure_code": procedure_code,
                        "line_charge": charge
                    }],
                    "diagnoses": [{
                        "icd10_code": diagnosis_code,
                        "description": diagnosis_desc
                    }]
                }
                
                # Validate
                st.session_state.current_claim = claim_dict
                validation_result = validate_claim_data(claim_dict)
                st.session_state.validation_result = validation_result
                
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"✅ Claim submitted for validation! Checking against requirements..."
                })
                
                st.session_state.current_view = "validate"
                st.rerun()
        
        if st.button("← Back", use_container_width=True):
            st.session_state.current_view = "home"
            st.rerun()
    
    # FREE TEXT INPUT VIEW
    elif st.session_state.current_view == "free_text":
        st.markdown("### 📝 Free Text Input")
        st.write("Enter claim information in any format. We'll parse it automatically.")
        
        with st.form("free_text_form"):
            claim_text = st.text_area(
                "Claim Details",
                height=200,
                placeholder="John Doe, DOB 01/15/1980, Dr. Jane Smith NPI 1234567890, "
                           "CPT 99213 on 2024-01-10 for $150, ICD-10 J45.901"
            )
            
            submitted = st.form_submit_button("📝 Parse & Validate", use_container_width=True)
            
            if submitted and claim_text:
                with st.spinner("Parsing text..."):
                    parsed = parse_free_text(claim_text)
                
                if parsed:
                    st.session_state.current_claim = parsed
                    st.json(parsed)
                    st.success("✅ Text parsed! Review and validate below.")
                    
                    if st.button("✅ Use This Data", use_container_width=True):
                        validation_result = validate_claim_data(parsed)
                        st.session_state.validation_result = validation_result
                        st.session_state.current_view = "validate"
                        st.rerun()
                else:
                    st.warning("⚠️ Could not parse text. Try filling the form manually.")
        
        if st.button("← Back", use_container_width=True):
            st.session_state.current_view = "home"
            st.rerun()
    
    # EDI 837P UPLOAD VIEW
    elif st.session_state.current_view == "edi_upload":
        st.markdown("### 📤 EDI 837P Upload")
        st.write("Upload an EDI 837P file for direct processing.")
        
        uploaded_file = st.file_uploader("Select EDI file", type=["837", "txt", "edi"])
        
        if uploaded_file:
            edi_content = uploaded_file.read().decode('utf-8', errors='ignore')
            
            if st.button("🔍 Parse EDI", use_container_width=True):
                with st.spinner("Parsing EDI file..."):
                    parsed = parse_edi_file(edi_content)
                
                if parsed:
                    st.success("✅ EDI parsed successfully!")
                    st.json(parsed, expanded=False)
                    
                    if st.button("✅ Use EDI Data", use_container_width=True):
                        st.session_state.current_claim = parsed
                        validation_result = validate_claim_data(parsed)
                        st.session_state.validation_result = validation_result
                        st.session_state.current_view = "validate"
                        st.rerun()
                else:
                    st.error("❌ Failed to parse EDI file. Ensure it's a valid 837P format.")
        
        if st.button("← Back", use_container_width=True):
            st.session_state.current_view = "home"
            st.rerun()
    
    # SETTINGS VIEW
    elif st.session_state.current_view == "settings":
        st.markdown("### ⚙️ Settings")
        
        st.subheader("📊 Saved Claims")
        if st.session_state.saved_claims:
            st.write(f"Total saved: {len(st.session_state.saved_claims)}")
            for idx, claim_path in enumerate(st.session_state.saved_claims[-5:], 1):
                st.caption(f"{idx}. {claim_path}")
        else:
            st.info("No saved claims yet")
        
        st.divider()
        
        st.subheader("🔧 Configuration")
        st.write(f"**AI Provider**: {Config.AI_PROVIDER.upper()}")
        st.write(f"**Ollama URL**: {Config.OLLAMA_URL}")
        st.write(f"**Available Models**: {len(get_available_models())}")
        
        st.divider()
        
        st.subheader("💾 Actions")
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("🔄 Clear Chat History", use_container_width=True):
                st.session_state.chat_history = []
                st.success("✅ Chat history cleared")
                st.rerun()
        
        with col_b:
            if st.button("🗑️ Reset All", use_container_width=True):
                for key in list(st.session_state.keys()):
                    if key not in ["chat_history"]:
                        del st.session_state[key]
                st.success("✅ Reset complete")
                st.rerun()
        
        st.divider()
        
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.current_view = "home"
            st.rerun()
    
    # VALIDATION VIEW
    elif st.session_state.current_view == "validate":
        st.markdown("### ✅ Validation Results")
        
        if not st.session_state.validation_result:
            st.info("📌 Fill and submit the form first to see validation results")
        else:
            result = st.session_state.validation_result
            
            # Display validation results
            display_validation_result(result)
            
            st.divider()
            
            # AI Explanation
            if st.button("🤖 Get AI Explanation"):
                with st.spinner("Getting AI explanation..."):
                    explanation = get_ai_explanation(result)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": explanation
                    })
                    st.write(explanation)
                    st.rerun()
            
            # Next steps
            st.divider()
            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                if st.button("📝 Edit Claim", use_container_width=True):
                    st.session_state.current_view = "fill_form"
                    st.rerun()
            with col_b:
                if st.button("💾 Save JSON", use_container_width=True):
                    success, path = save_claim_to_file(result)
                    if success:
                        st.success(f"✅ Saved to: {path}")
                        st.session_state.saved_claims.append(path)
                    else:
                        st.error(f"❌ Save failed: {path}")
            with col_c:
                if st.button("📤 Export EDI", use_container_width=True):
                    st.info("EDI export feature coming soon")
            with col_d:
                if st.button("🏠 Home", use_container_width=True):
                    st.session_state.current_view = "home"
                    st.rerun()

st.divider()
st.caption(f"OptiClaimAI v2.0 | {Config.AI_PROVIDER.upper()} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
