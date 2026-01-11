"""
OptiClaimAI - Human-Friendly Claims Intelligence Platform
Main Streamlit Application with Multi-Mode Input
"""

import streamlit as st
from streamlit_ui.form_input import render_form_mode
from streamlit_ui.text_input import render_text_mode
from streamlit_ui.results_display import render_results
from streamlit_ui.edi_mode import render_edi_mode
from model.claim_builder import ClaimBuilder
from engine.rules_engine_v2 import ClaimRulesEngine
from engine.ai_engine import OllamaEngine
import logging

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="OptiClaimAI - Claims Intelligence",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    """Initialize all session state variables"""
    if 'mode' not in st.session_state:
        st.session_state.mode = None
    if 'claim' not in st.session_state:
        st.session_state.claim = None
    if 'validation_result' not in st.session_state:
        st.session_state.validation_result = None
    if 'show_results' not in st.session_state:
        st.session_state.show_results = False

init_session_state()

# Main title
st.markdown('<div class="main-title">🏥 OptiClaimAI</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Claims Intelligence for Humans (Not EDI Experts)</div>', unsafe_allow_html=True)

# PHI Warning
st.warning("⚠️ **Demo Mode**: Do NOT submit real patient data. Use synthetic/de-identified data only for testing.")

st.divider()

# Entry point - mode selection
if st.session_state.mode is None:
    st.markdown("### How do you want to submit your claim?")
    
    col1, col2, col3 = st.columns(3, gap="large")
    
    with col1:
        if st.button(
            "📋 **Use Form**\n\nStep-by-step guided form\nfor claim entry",
            use_container_width=True,
            key="btn_form",
            help="Fill out a structured form with guided fields"
        ):
            st.session_state.mode = 'form'
            st.rerun()
    
    with col2:
        if st.button(
            "📝 **Describe It**\n\nNatural language\nclaim entry",
            use_container_width=True,
            key="btn_text",
            help="Tell us about the visit in plain English"
        ):
            st.session_state.mode = 'text'
            st.rerun()
    
    with col3:
        if st.button(
            "⬆️ **Upload EDI**\n\nAdvanced mode\n837 file upload",
            use_container_width=True,
            key="btn_edi",
            help="Upload a standard 837 EDI file"
        ):
            st.session_state.mode = 'edi'
            st.rerun()

# Mode handlers
elif st.session_state.mode == 'form':
    form_data = render_form_mode()
    if form_data:
        try:
            # Build claim from form
            claim = ClaimBuilder.from_form(form_data)
            
            # Validate
            engine = ClaimRulesEngine()
            validation = engine.validate(claim)
            
            # Store in session
            st.session_state.claim = claim
            st.session_state.validation_result = validation
            st.session_state.show_results = True
            
            # Display results
            render_results(claim, validation)
            
            # Back button
            st.divider()
            if st.button("← Back to Input Mode", use_container_width=True):
                st.session_state.mode = None
                st.session_state.claim = None
                st.session_state.validation_result = None
                st.rerun()
        
        except Exception as e:
            st.error(f"❌ Error processing claim: {str(e)}")
            st.exception(e)

elif st.session_state.mode == 'text':
    text_input = render_text_mode()
    if text_input:
        try:
            # Parse text into claim
            claim = ClaimBuilder.from_text(text_input)
            
            if claim:
                # Validate
                engine = ClaimRulesEngine()
                validation = engine.validate(claim)
                
                # Store in session
                st.session_state.claim = claim
                st.session_state.validation_result = validation
                st.session_state.show_results = True
                
                # Display results
                render_results(claim, validation)
                
                # Back button
                st.divider()
                if st.button("← Back to Input Mode", use_container_width=True):
                    st.session_state.mode = None
                    st.session_state.claim = None
                    st.session_state.validation_result = None
                    st.rerun()
            else:
                st.error("❌ Could not parse claim. Try being more specific with names, dates, and codes.")
        
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.exception(e)

elif st.session_state.mode == 'edi':
    render_edi_mode()
    
    st.divider()
    if st.button("← Back to Input Mode", use_container_width=True):
        st.session_state.mode = None
        st.session_state.claim = None
        st.session_state.validation_result = None
        st.rerun()

# Sidebar
with st.sidebar:
    st.header("ℹ️ About OptiClaimAI")
    
    st.markdown("""
    OptiClaimAI makes healthcare claims easy for humans.
    
    **Features:**
    - 📋 Simple form input
    - 📝 Natural language parsing
    - 🔍 Smart validation
    - ⚠️ Denial risk prediction
    - 💡 AI-powered explanations (optional)
    - ⬆️ EDI file support (advanced)
    
    **Technology:**
    - Zero paid APIs
    - Local Ollama for AI
    - Open source
    """)
    
    st.divider()
    
    st.subheader("🤖 AI Status")
    ai_engine = OllamaEngine()
    if ai_engine.available:
        st.success("✅ Ollama is running - AI features enabled")
    else:
        st.warning("⚠️ Ollama not available - AI features disabled")
        st.caption("To enable AI: install Ollama and run `ollama serve`")
    
    st.divider()
    
    if st.session_state.claim:
        st.success("✅ Claim Loaded")
        st.caption(f"Patient: {st.session_state.claim.patient.first_name} {st.session_state.claim.patient.last_name}")
        st.caption(f"Total: ${st.session_state.claim.claim_amount:,.2f}")
        
        if st.button("🔄 Reset Application", use_container_width=True):
            st.session_state.mode = None
            st.session_state.claim = None
            st.session_state.validation_result = None
            st.rerun()
    else:
        st.info("📁 No claim loaded yet")
    
    st.divider()
    
    st.caption("OptiClaimAI v1.0 MVP • Claims Intelligence Platform")

if __name__ == "__main__":
    pass
