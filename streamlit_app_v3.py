"""
OptiClaimAI Main Application - v3 (Streamlit Compliant)
Strict execution model: Render → Submit → Validate → Process → Display
"""

import streamlit as st
from streamlit_ui.cms1500_form_v3 import render_cms1500_form
from streamlit_ui.form_input import render_form_mode
from streamlit_ui.text_input import render_text_mode
from streamlit_ui.edi_mode import render_edi_mode
from engine.validate_cms1500 import validate_cms1500, build_cms1500_object
from engine.nppes_lookup import get_nppes_lookup
from engine.edi_837p_generator import cms1500_to_edi837p
from engine.ai_engine_factory import is_ai_enabled, get_ai_engine
import json


# Page configuration
st.set_page_config(
    page_title="OptiClaimAI - Claims Intelligence",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
def init_session_state():
    """Initialize all session state variables"""
    if 'mode' not in st.session_state:
        st.session_state.mode = 'cms1500'
    if 'submitted_data' not in st.session_state:
        st.session_state.submitted_data = None
    if 'validation_errors' not in st.session_state:
        st.session_state.validation_errors = []
    if 'validation_warnings' not in st.session_state:
        st.session_state.validation_warnings = []


init_session_state()

# Header
st.markdown("""
<div style="text-align: center; margin-bottom: 2rem;">
    <h1 style="color: #1f77b4;">🏥 OptiClaimAI</h1>
    <p style="color: #666; font-size: 1.1rem;">Healthcare Claims Intelligence Platform</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Options")
    
    # Mode selection
    st.subheader("Input Mode")
    mode = st.radio(
        "Select input method:",
        options=["📋 CMS-1500", "📝 Form", "📄 Text", "📊 EDI"],
        key="mode_selector"
    )
    
    if mode == "📋 CMS-1500":
        st.session_state.mode = 'cms1500'
    elif mode == "📝 Form":
        st.session_state.mode = 'form'
    elif mode == "📄 Text":
        st.session_state.mode = 'text'
    elif mode == "📊 EDI":
        st.session_state.mode = 'edi'
    
    # AI Settings (disabled by default)
    st.subheader("AI Settings")
    ai_enabled = st.checkbox("Enable AI (Optional)", value=False)
    if ai_enabled:
        ai_provider = st.selectbox("AI Provider", ["ollama", "openai"], key="ai_provider")
        if ai_provider == "openai":
            api_key = st.text_input("OpenAI API Key", type="password", key="openai_key")
        else:
            api_key = None
    else:
        ai_provider = None
        api_key = None
    
    st.divider()
    st.caption("All processing is local and secure.")


# Main content area
if st.session_state.mode == 'cms1500':
    # ===== CMS-1500 MODE =====
    form_data = render_cms1500_form()
    
    # PHASE 2: SUBMIT PHASE (only if form was submitted)
    if form_data is not None:
        st.divider()
        st.header("Processing Claim...")
        
        # PHASE 3: VALIDATION
        is_valid, errors, warnings = validate_cms1500(form_data)
        
        if errors:
            st.error("❌ **Form Validation Failed**")
            for error in errors:
                st.error(f"• {error}")
            st.stop()
        
        if warnings:
            st.warning("⚠️ **Warnings (non-blocking)**")
            for warning in warnings:
                st.warning(f"• {warning}")
        
        # PHASE 4: BUILD CMS1500 OBJECT
        try:
            cms1500 = build_cms1500_object(form_data)
        except Exception as e:
            st.error(f"Failed to build claim object: {str(e)}")
            st.stop()
        
        # PHASE 5: OPTIONAL NPPES LOOKUP (post-submit)
        with st.expander("🔍 Provider Information (from NPPES)"):
            if form_data.get('provider_npi'):
                if st.button("Look up Provider"):
                    with st.spinner("Searching NPPES..."):
                        nppes = get_nppes_lookup()
                        nppes_result = nppes.lookup_npi(form_data['provider_npi'])
                        
                        if nppes_result:
                            st.success("Provider found!")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**Name:** {nppes_result.get('first_name')} {nppes_result.get('last_name')}")
                                st.write(f"**Specialty:** {nppes_result.get('specialty', 'N/A')}")
                            with col2:
                                st.write(f"**Address:** {nppes_result.get('address', 'N/A')}")
                                st.write(f"**Phone:** {nppes_result.get('phone', 'N/A')}")
                        else:
                            st.info("Provider not found in NPPES (may be new or inactive)")
        
        # PHASE 6: OPTIONAL AI EXPLANATION (if enabled)
        if is_ai_enabled():
            with st.expander("🤖 AI Claim Analysis (Optional)"):
                st.info("AI analysis is disabled. Enable in sidebar to use.")
        
        # PHASE 7: EDI GENERATION
        st.header("📄 X12 837P EDI Output")
        try:
            edi_output = cms1500_to_edi837p(cms1500)
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"✅ **EDI Generated ({len(edi_output)} characters)**")
            with col2:
                st.write(f"**Claim:** {form_data.get('claim_number', 'N/A')}")
            
            # Display EDI (truncated)
            with st.expander("View Full EDI"):
                st.code(edi_output, language="text")
            
            # Download buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.download_button(
                    label="📥 Download .837 File",
                    data=edi_output,
                    file_name=f"claim_{form_data.get('claim_number', 'unknown')}.837",
                    mime="application/octet-stream"
                )
            
            with col2:
                st.download_button(
                    label="📥 Download JSON",
                    data=json.dumps(cms1500.to_dict(), indent=2, default=str),
                    file_name=f"claim_{form_data.get('claim_number', 'unknown')}.json",
                    mime="application/json"
                )
            
            with col3:
                if st.button("🔄 Submit Another Claim"):
                    st.session_state.submitted_data = None
                    st.rerun()
        
        except Exception as e:
            st.error(f"Failed to generate EDI: {str(e)}")
            st.stop()

elif st.session_state.mode == 'form':
    render_form_mode()

elif st.session_state.mode == 'text':
    render_text_mode()

elif st.session_state.mode == 'edi':
    render_edi_mode()

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #999; font-size: 0.9rem; margin-top: 2rem;">
    <p>OptiClaimAI v3.0 | X12 837P Compliant | No AI Dependencies | Streamlit Cloud Ready</p>
</div>
""", unsafe_allow_html=True)
