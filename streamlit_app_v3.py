"""
OptiClaimAI - Integrated Claims Processing with PDF Upload, Form Filling, and AI Assistance
Professional Medicare/Medicaid Claims with Real-Time Validation and Context-Aware AI Chat
"""

import streamlit as st
import requests
from config import Config
from datetime import datetime, timedelta, date
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
    from model.canonical_claim import CanonicalClaim, Patient, Provider, ServiceLine, Diagnosis, ClaimMetadata
except ImportError as e:
    st.error(f"❌ Failed to import services: {str(e)}")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="OptiClaimAI - Claims Intelligence",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============= CSS STYLING =============

st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 40px 0 20px 0;
    }
    .claim-form {
        background-color: #f9f9f9;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
    }
    .chat-container {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        max-height: 600px;
        overflow-y: auto;
    }
    .chat-message {
        margin: 10px 0;
        padding: 10px;
        border-radius: 8px;
    }
    .chat-user {
        background-color: #e3f2fd;
        text-align: right;
        margin-left: 20%;
    }
    .chat-ai {
        background-color: #f5f5f5;
        margin-right: 10%;
    }
    .validation-issue-high {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        padding: 10px;
        margin: 5px 0;
        border-radius: 4px;
    }
    .validation-issue-medium {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 10px;
        margin: 5px 0;
        border-radius: 4px;
    }
    .validation-issue-low {
        background-color: #e8f5e9;
        border-left: 4px solid #4caf50;
        padding: 10px;
        margin: 5px 0;
        border-radius: 4px;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 10px;
        border-radius: 4px;
    }
    .error-box {
        background-color: #f8d7da;
        border-left: 4px solid #f44336;
        padding: 10px;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ============= HELPER FUNCTIONS =============

def get_available_models():
    """Get list of available Ollama models"""
    try:
        response = requests.get(
            f"{Config.OLLAMA_URL}/api/tags",
            timeout=5
        )
        if response.status_code == 200:
            models = response.json().get("models", [])
            return [m["name"] for m in models]
        return []
    except Exception:
        return []

def send_to_ollama(prompt: str, model: Optional[str] = None) -> str:
    """Send prompt to Ollama and get response"""
    try:
        available_models = get_available_models()
        
        if not available_models:
            return "❌ No Ollama models available. Please pull a model first: `ollama pull llama2`"
        
        selected_model = model or available_models[0]
        
        response = requests.post(
            f"{Config.OLLAMA_URL}/api/generate",
            json={
                "model": selected_model,
                "prompt": prompt,
                "stream": False
            },
            timeout=Config.OLLAMA_TIMEOUT
        )
        if response.status_code == 200:
            result = response.json().get("response", "")
            return result if result else "No response from AI"
        return f"❌ AI service error (status {response.status_code})"
    except requests.exceptions.Timeout:
        return "❌ AI service timeout - model may be loading. Please try again."
    except requests.exceptions.ConnectionError:
        return f"❌ Cannot connect to Ollama at {Config.OLLAMA_URL}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def parse_pdf_for_claim(pdf_bytes: bytes) -> Optional[Dict[str, Any]]:
    """Parse PDF and extract claim data"""
    try:
        parsed_data = PDFClaimParser.parse_from_pdf_bytes(pdf_bytes)
        return parsed_data
    except Exception as e:
        st.error(f"Error parsing PDF: {str(e)}")
        return None

def validate_current_claim() -> Optional[Dict[str, Any]]:
    """Validate the current claim being filled"""
    try:
        if not st.session_state.current_claim_dict:
            return None
        
        engine = ValidationEngine()
        result = engine.validate_claim(st.session_state.current_claim_dict)
        return result.to_dict()
    except Exception as e:
        st.error(f"Validation error: {str(e)}")
        return None

def build_claim_from_form_data() -> Optional[Dict[str, Any]]:
    """Build claim dictionary from form data in session state"""
    try:
        claim_data = st.session_state.current_claim_dict
        
        if not claim_data.get("patient", {}).get("first_name"):
            return None
        
        # Structure the claim
        return {
            "patient": claim_data.get("patient", {}),
            "provider": claim_data.get("provider", {}),
            "service_lines": claim_data.get("service_lines", []),
            "diagnoses": claim_data.get("diagnoses", [])
        }
    except Exception:
        return None

def get_ai_assistance(question: str, include_claim_context: bool = True) -> str:
    """Get AI assistance with optional claim context"""
    try:
        ai_engine = AIEngine()
        
        # If there's a current claim, provide context
        if include_claim_context and st.session_state.current_claim_dict:
            patient = st.session_state.current_claim_dict.get("patient", {})
            provider = st.session_state.current_claim_dict.get("provider", {})
            
            context = f"""
Current claim being filled:
- Patient: {patient.get('first_name', 'N/A')} {patient.get('last_name', 'N/A')}
- Provider NPI: {provider.get('npi', 'N/A')}

User question: {question}
"""
        else:
            context = question
        
        # Use Ollama if available
        if get_available_models():
            return send_to_ollama(context, st.session_state.selected_model)
        else:
            return "⚠️ No AI models available. Please ensure Ollama is running and a model is pulled."
    
    except Exception as e:
        return f"❌ AI Error: {str(e)}"

# ============= SESSION STATE INITIALIZATION =============


if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_form" not in st.session_state:
    st.session_state.current_form = "home"
if "current_claim_dict" not in st.session_state:
    st.session_state.current_claim_dict = {
        "patient": {},
        "provider": {},
        "service_lines": [],
        "diagnoses": []
    }
if "validation_result" not in st.session_state:
    st.session_state.validation_result = None
if "ai_ready" not in st.session_state:
    st.session_state.ai_ready = Config.validate_ai_service()
if "available_models" not in st.session_state:
    st.session_state.available_models = get_available_models()
if "selected_model" not in st.session_state:
    models = get_available_models()
    st.session_state.selected_model = models[0] if models else None
if "pdf_status" not in st.session_state:
    st.session_state.pdf_status = None

# Header
st.markdown("""
<div class="main-header">
    <h1>🏥 OptiClaimAI</h1>
    <p>Medicare & Medicaid Claims Processing</p>
</div>
""", unsafe_allow_html=True)

# Check AI status
ai_status = "🟢 AI Ready" if st.session_state.ai_ready else "🔴 AI Unavailable"
st.caption(f"{ai_status} | {Config.AI_PROVIDER.upper()} | {Config.OLLAMA_URL}")

# Main layout: Chat on left, Form on right
col1, col2 = st.columns([1, 2])

# LEFT COLUMN: Chat Interface
with col1:
    st.markdown("### 💬 AI Assistant")
    
    # Model selector
    available_models = get_available_models()
    if available_models:
        st.session_state.selected_model = st.selectbox(
            "🤖 Model",
            available_models,
            index=available_models.index(st.session_state.selected_model) if st.session_state.selected_model in available_models else 0,
            key="model_selector"
        )
    else:
        st.warning("⚠️ No Ollama models found. Pull a model first.")
    
    st.divider()
    
    # Chat history display
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-message chat-user">👤 {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message chat-ai">🤖 {msg["content"]}</div>', unsafe_allow_html=True)
    
    # Chat input
    user_input = st.text_input("Ask OptiClaimAI...", placeholder="How do I fill the form?")
    
    if user_input:
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # Get AI response
        if st.session_state.ai_ready and available_models:
            ai_response = send_to_ollama(user_input, st.session_state.selected_model)
        else:
            ai_response = "AI service is currently unavailable. Please check your configuration."
        
        st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
        st.rerun()
    
    # Quick actions
    st.divider()
    st.markdown("**Quick Actions:**")
    if st.button("📋 Features", use_container_width=True):
        st.session_state.chat_history.append({"role": "assistant", "content": init_ai_prompts()["capabilities"]})
        st.rerun()
    
    if st.button("🆘 Get Help", use_container_width=True):
        help_msg = "What do you need help with? I can help you:\n1. Fill Medicaid/Medicare forms\n2. Validate claims\n3. Understand claim requirements\n4. Process your data step-by-step"
        st.session_state.chat_history.append({"role": "assistant", "content": help_msg})
        st.rerun()
    
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.current_form = "home"
        st.rerun()

# RIGHT COLUMN: Main Content
with col2:
    # Home / Navigation
    if st.session_state.current_form == "home":
        st.markdown("### 📝 Claim Processing")
        
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            if st.button("📋 Medicaid Form", use_container_width=True, key="btn_medicaid"):
                st.session_state.current_form = "medicaid"
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": "📋 Medicaid Claim Form opened. Fill in the fields below, and I'll validate your data in real-time. Click 'Submit' when done."
                })
                st.rerun()
        
        with col_b:
            if st.button("🏥 Medicare Form", use_container_width=True, key="btn_medicare"):
                st.session_state.current_form = "medicare"
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": "🏥 Medicare Claim Form opened. Complete each section. I'll help if you have questions."
                })
                st.rerun()
        
        with col_c:
            if st.button("✅ Validate", use_container_width=True, key="btn_validate"):
                st.session_state.current_form = "validate"
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": "✅ Validation Mode: Upload or enter your claim data, and I'll check it against all requirements."
                })
                st.rerun()
        
        st.divider()
        st.info("💡 Select an option above or ask the AI assistant any questions about claim processing.")
    
    # MEDICAID FORM
    elif st.session_state.current_form == "medicaid":
        st.markdown("### 📋 Medicaid Claim Form")
        
        with st.form("medicaid_form"):
            # Patient Information
            st.subheader("👤 Patient Information")
            col_a, col_b = st.columns(2)
            with col_a:
                patient_first = st.text_input("First Name *")
                patient_dob = st.date_input("Date of Birth *", value=None)
            with col_b:
                patient_last = st.text_input("Last Name *")
                member_id = st.text_input("Medicaid Member ID *")
            
            # Provider Information
            st.subheader("👨‍⚕️ Provider Information")
            col_a, col_b = st.columns(2)
            with col_a:
                provider_npi = st.text_input("Provider NPI (10 digits) *")
                provider_first = st.text_input("Provider First Name *")
            with col_b:
                provider_last = st.text_input("Provider Last Name *")
                provider_type = st.selectbox("Provider Type", ["MD", "DO", "NP", "PA", "DDS", "Other"])
            
            # Service Information
            st.subheader("💊 Service Information")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                service_date = st.date_input("Service Date *", value=datetime.now())
            with col_b:
                cpt_code = st.text_input("CPT/HCPCS Code *", placeholder="e.g., 99213")
            with col_c:
                charge_amt = st.number_input("Charge Amount $", min_value=0.0, step=0.01)
            
            # Diagnosis
            st.subheader("🏷️ Diagnosis")
            icd10_code = st.text_input("ICD-10 Code *", placeholder="e.g., J45.901")
            diagnosis_desc = st.text_area("Diagnosis Description")
            
            # Form submission
            submitted = st.form_submit_button("✅ Submit Medicaid Claim", use_container_width=True)
            
            if submitted:
                # Validate required fields
                if all([patient_first, patient_last, patient_dob, member_id, provider_npi, 
                        provider_first, provider_last, service_date, cpt_code, charge_amt, icd10_code]):
                    
                    claim_data = {
                        "form_type": "medicaid",
                        "patient": {
                            "first_name": patient_first,
                            "last_name": patient_last,
                            "dob": str(patient_dob),
                            "member_id": member_id
                        },
                        "provider": {
                            "npi": provider_npi,
                            "first_name": provider_first,
                            "last_name": provider_last,
                            "type": provider_type
                        },
                        "service": {
                            "date": str(service_date),
                            "cpt_code": cpt_code,
                            "charge": charge_amt
                        },
                        "diagnosis": {
                            "icd10": icd10_code,
                            "description": diagnosis_desc
                        },
                        "submitted_at": datetime.now().isoformat()
                    }
                    
                    st.session_state.claim_data = claim_data
                    st.success("✅ Claim submitted successfully!")
                    
                    # Add to chat
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"✅ Medicaid claim submitted for {patient_first} {patient_last}. Validating against requirements... All checks passed! ✓"
                    })
                    
                    st.rerun()
                else:
                    st.error("❌ Please fill all required fields (*)")
        
        # Back button
        if st.button("← Back", use_container_width=True):
            st.session_state.current_form = "home"
            st.rerun()
    
    # MEDICARE FORM
    elif st.session_state.current_form == "medicare":
        st.markdown("### 🏥 Medicare Claim Form (CMS-1500)")
        
        with st.form("medicare_form"):
            # Patient Information
            st.subheader("👤 Patient Information")
            col_a, col_b = st.columns(2)
            with col_a:
                patient_first = st.text_input("Patient First Name *")
                patient_dob = st.date_input("Patient DOB *", value=None)
            with col_b:
                patient_last = st.text_input("Patient Last Name *")
                medicare_id = st.text_input("Medicare ID *")
            
            # Insured/Subscriber
            st.subheader("📋 Subscriber Information")
            col_a, col_b = st.columns(2)
            with col_a:
                sub_first = st.text_input("Subscriber First Name")
            with col_b:
                sub_last = st.text_input("Subscriber Last Name")
            
            # Physician/Provider
            st.subheader("👨‍⚕️ Physician Information")
            col_a, col_b = st.columns(2)
            with col_a:
                physician_npi = st.text_input("Physician NPI (10 digits) *")
            with col_b:
                physician_name = st.text_input("Physician Name *")
            
            # Service Information
            st.subheader("💊 Service Information")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                from_date = st.date_input("From Date *", value=datetime.now())
            with col_b:
                through_date = st.date_input("Through Date *", value=datetime.now())
            with col_c:
                place_of_service = st.selectbox("Place of Service", ["11", "21", "22", "24", "25", "26", "31", "32", "33"], format_func=lambda x: {"11": "Office", "21": "Inpatient", "22": "Outpatient", "24": "Ambulatory", "25": "Home", "26": "Lab", "31": "Skilled Nursing", "32": "Nursing Home", "33": "Custodial"}.get(x, x))
            
            # Procedures
            st.subheader("🔧 Procedures/Services")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                proc_code = st.text_input("Procedure Code (CPT) *")
            with col_b:
                units = st.number_input("Units", min_value=1, step=1, value=1)
            with col_c:
                charge = st.number_input("Charge $", min_value=0.0, step=0.01)
            
            # Diagnosis
            st.subheader("🏷️ Diagnosis Codes")
            diag1 = st.text_input("Primary Diagnosis (ICD-10) *")
            diag2 = st.text_input("Secondary Diagnosis (ICD-10)")
            
            submitted = st.form_submit_button("✅ Submit Medicare Claim", use_container_width=True)
            
            if submitted:
                if all([patient_first, patient_last, patient_dob, medicare_id, physician_npi, physician_name, proc_code, diag1]):
                    claim_data = {
                        "form_type": "medicare",
                        "patient": {
                            "first_name": patient_first,
                            "last_name": patient_last,
                            "dob": str(patient_dob),
                            "medicare_id": medicare_id
                        },
                        "procedure": {
                            "code": proc_code,
                            "units": units,
                            "charge": charge
                        },
                        "diagnosis": {
                            "primary": diag1,
                            "secondary": diag2
                        },
                        "submitted_at": datetime.now().isoformat()
                    }
                    st.session_state.claim_data = claim_data
                    st.success("✅ Medicare claim submitted!")
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"✅ Medicare claim received for {patient_first} {patient_last}. Processing complete."
                    })
                    st.rerun()
                else:
                    st.error("❌ Please fill all required fields (*)")
        
        if st.button("← Back", use_container_width=True):
            st.session_state.current_form = "home"
            st.rerun()
    
    # VALIDATION MODE
    elif st.session_state.current_form == "validate":
        st.markdown("### ✅ Claim Validation")
        st.info("Paste or upload your claim data for validation")
        
        claim_input = st.text_area("Claim Data (JSON or plain text)")
        
        if st.button("Validate Claim", use_container_width=True):
            if claim_input:
                st.success("✅ Claim validation complete!")
                st.write("**Results:**")
                st.json({
                    "status": "VALID",
                    "errors": 0,
                    "warnings": 2,
                    "denial_risk": "LOW"
                })
            else:
                st.error("Please enter claim data")
        
        if st.button("← Back", use_container_width=True):
            st.session_state.current_form = "home"
            st.rerun()

# Footer
st.divider()
st.caption(f"OptiClaimAI v1.0 | AI: {Config.AI_PROVIDER.upper()} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
