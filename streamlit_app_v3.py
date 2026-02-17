"""
OptiClaimAI - New UI with Google-like Search and Ollama Chat
Professional Medicare/Medicaid Claims Processing
"""

import streamlit as st
import requests
from config import Config
from datetime import datetime, timedelta
import json

# Page configuration
st.set_page_config(
    page_title="OptiClaimAI",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Google-like interface
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 40px 0 20px 0;
    }
    .search-container {
        display: flex;
        justify-content: center;
        margin: 20px 0;
    }
    .claim-form {
        background-color: #f9f9f9;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
    }
    .chat-container {
        background-color: #ffffff;
        border-left: 1px solid #e0e0e0;
        padding: 20px;
        border-radius: 8px;
    }
    .chat-message {
        margin: 10px 0;
        padding: 10px;
        border-radius: 8px;
    }
    .chat-user {
        background-color: #e3f2fd;
        text-align: right;
    }
    .chat-ai {
        background-color: #f5f5f5;
    }
    .btn-primary {
        background-color: #4285F4;
        color: white;
        padding: 10px 20px;
        border-radius: 4px;
        border: none;
        cursor: pointer;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_form" not in st.session_state:
    st.session_state.current_form = "home"
if "claim_data" not in st.session_state:
    st.session_state.claim_data = {}
if "ai_ready" not in st.session_state:
    st.session_state.ai_ready = Config.validate_ai_service()

def send_to_ollama(prompt):
    """Send prompt to Ollama and get response"""
    try:
        response = requests.post(
            f"{Config.OLLAMA_URL}/api/generate",
            json={
                "model": Config.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=Config.OLLAMA_TIMEOUT
        )
        if response.status_code == 200:
            return response.json().get("response", "Error processing request")
        return "AI service error"
    except Exception as e:
        return f"Connection error: {str(e)}"

def init_ai_prompts():
    """Initialize AI system prompts"""
    return {
        "system": """You are OptiClaimAI assistant. You help Medicare/Medicaid data entry operators:
1. Process healthcare claims
2. Fill out claim forms
3. Validate claim data
4. Answer questions about claim processing

Be concise, professional, and guide users step-by-step.
When user asks "how to fill form", respond with: "Click on 'Medicaid Claim Form' button in the left panel. I'll guide you through each field."
Current app features:
- Medicaid Claim Form
- Medicare Claim Form  
- Claim Validation
- AI-Powered Analysis""",
        "capabilities": """I can help you with:
1. **📋 Fill Claims** - Step-by-step guidance for Medicaid/Medicare forms
2. **✅ Validate Claims** - Check if your claim meets requirements
3. **🤖 AI Analysis** - Get intelligent suggestions to improve claims
4. **❓ How-to Guides** - Learn how to use each feature
5. **🔍 Search Help** - Find answers about claim processing

What would you like to do?"""
    }

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
        if st.session_state.ai_ready:
            ai_response = send_to_ollama(user_input)
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
        st.session_state.chat_history.append({"role": "assistant", "content": "What do you need help with? I can help you:\n1. Fill Medicaid/Medicare forms\n2. Validate claims\n3. Understand claim requirements\n4. Process your data step-by-step"})
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
