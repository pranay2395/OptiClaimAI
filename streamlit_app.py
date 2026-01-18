"""
OptiClaimAI - Production Application
Unified interface for all claim input modes
"""

import streamlit as st
import pandas as pd
import json
from typing import Dict, List, Optional
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Core imports
from engine.parser import EDI837Parser
from engine.validator import ClaimValidator
from engine.analytics import ClaimsAnalytics

# Multi-mode UI imports
try:
    from streamlit_ui.form_input import render_form_mode
    from streamlit_ui.text_input import render_text_mode
    from streamlit_ui.edi_mode import render_edi_mode
    from streamlit_ui.cms1500_form_v3 import render_cms1500_form
    from streamlit_ui.results_display import render_results
except ImportError:
    render_form_mode = None
    render_text_mode = None
    render_edi_mode = None
    render_cms1500_form = None
    render_results = None

# Model and engine imports
try:
    from model.cms1500_schema import CMS1500
    from engine.validate_cms1500 import validate_cms1500, build_cms1500_object
    from engine.edi_837p_generator import cms1500_to_edi837p
    from engine.nppes_lookup import get_nppes_lookup
    from engine.ai_engine_factory import is_ai_enabled, get_ai_engine
except ImportError:
    pass

# Page configuration
st.set_page_config(
    page_title="OptiClaimAI - Healthcare Claims Intelligence",
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
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    """Initialize all session state variables"""
    if 'mode' not in st.session_state:
        st.session_state.mode = None
    if 'parsed_claims' not in st.session_state:
        st.session_state.parsed_claims = None
    if 'validation_results' not in st.session_state:
        st.session_state.validation_results = None
    if 'analytics_data' not in st.session_state:
        st.session_state.analytics_data = None
    if 'file_uploaded' not in st.session_state:
        st.session_state.file_uploaded = False
    if 'file_name' not in st.session_state:
        st.session_state.file_name = None
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    if 'claim' not in st.session_state:
        st.session_state.claim = None
    if 'validation_result' not in st.session_state:
        st.session_state.validation_result = None

init_session_state()

# ============= HELPER FUNCTIONS =============

def parse_uploaded_file(file_content: str, file_name: str) -> Optional[Dict]:
    """Parse uploaded EDI 837 file"""
    try:
        with st.spinner('🔄 Parsing EDI 837 file...'):
            parser = EDI837Parser()
            parsed_data = parser.parse(file_content)

            if not parsed_data or 'claims' not in parsed_data:
                st.error("❌ No claims found in file")
                return None

            st.success(f"✅ Successfully parsed {len(parsed_data['claims'])} claim(s)")
            return parsed_data

    except Exception as e:
        st.error(f"❌ Parsing Error: {str(e)}")
        return None

def validate_claims(parsed_data: Dict) -> Optional[List[Dict]]:
    """Validate parsed claims"""
    try:
        with st.spinner('🔍 Validating claims...'):
            validator = ClaimValidator()
            validation_results = validator.validate_all(parsed_data)

            total_errors = sum(len(result.get('errors', [])) for result in validation_results)
            total_warnings = sum(len(result.get('warnings', [])) for result in validation_results)

            if total_errors == 0:
                st.success(f"✅ All claims validated successfully ({total_warnings} warnings)")
            else:
                st.warning(f"⚠️ Validation complete: {total_errors} errors, {total_warnings} warnings")

            return validation_results

    except Exception as e:
        st.error(f"❌ Validation Error: {str(e)}")
        return None

def generate_analytics(parsed_data: Dict, validation_results: List[Dict]) -> Optional[Dict]:
    """Generate analytics from claims data"""
    try:
        with st.spinner('📊 Generating analytics...'):
            analytics_engine = ClaimsAnalytics()
            analytics_data = analytics_engine.analyze(parsed_data, validation_results)

            if analytics_data:
                st.success("✅ Analytics generated successfully")

            return analytics_data

    except Exception as e:
        st.error(f"❌ Analytics Error: {str(e)}")
        return None

# ============= MAIN APPLICATION =============

# Header
st.markdown("""
<div style="text-align: center; margin-bottom: 2rem;">
    <h1 style="color: #1f77b4;">🏥 OptiClaimAI</h1>
    <p style="color: #666; font-size: 1.1rem;">Healthcare Claims Intelligence Platform</p>
</div>
""", unsafe_allow_html=True)

st.warning("⚠️ **Demo Mode**: Do NOT submit real patient data. Use synthetic/de-identified data only.")
st.divider()

# Sidebar
with st.sidebar:
    st.header("⚙️ Navigation")
    
    mode_select = st.radio(
        "Select Input Mode:",
        options=["📋 CMS-1500", "📝 Form", "📄 Text", "📊 EDI Parser", "📈 Analytics"],
        key="mode_selector"
    )
    
    if mode_select == "📋 CMS-1500":
        st.session_state.mode = 'cms1500'
    elif mode_select == "📝 Form":
        st.session_state.mode = 'form'
    elif mode_select == "📄 Text":
        st.session_state.mode = 'text'
    elif mode_select == "📊 EDI Parser":
        st.session_state.mode = 'edi'
    elif mode_select == "📈 Analytics":
        st.session_state.mode = 'analytics'
    
    st.divider()
    
    st.subheader("About")
    st.markdown("""
    OptiClaimAI is a healthcare claims intelligence platform that supports:
    
    - **CMS-1500** - Complete form with EDI generation
    - **Form** - Guided form entry
    - **Text** - Natural language parsing
    - **EDI Upload** - Direct 837P file analysis
    - **Analytics** - Claims insights
    
    **Technology:**
    - X12 837P Compliant
    - Local Processing (No Cloud)
    - Optional AI (Ollama)
    """)
    
    st.divider()
    
    if st.button("🔄 Reset", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# ============= MODE ROUTING =============

if st.session_state.mode is None or st.session_state.mode == 'cms1500':
    st.header("📋 CMS-1500 Form")
    
    if render_cms1500_form is not None:
        form_data = render_cms1500_form()
        
        if form_data is not None:
            st.divider()
            st.subheader("✅ Form Submitted")
            
            # Validate
            try:
                is_valid, errors, warnings = validate_cms1500(form_data)
                
                if errors:
                    st.error("❌ **Validation Errors**")
                    for error in errors:
                        st.error(f"• {error}")
                    st.stop()
                
                if warnings:
                    st.warning("⚠️ **Warnings (non-blocking)**")
                    for warning in warnings:
                        st.warning(f"• {warning}")
                
                # Build CMS1500 object
                cms1500 = build_cms1500_object(form_data)
                
                # Optional NPPES lookup
                with st.expander("🔍 Provider Information"):
                    if form_data.get('provider_npi'):
                        if st.button("Look up Provider"):
                            nppes = get_nppes_lookup()
                            result = nppes.lookup_npi(form_data['provider_npi'])
                            if result:
                                st.success("Provider found!")
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write(f"**Name:** {result.get('first_name')} {result.get('last_name')}")
                                    st.write(f"**Specialty:** {result.get('specialty', 'N/A')}")
                                with col2:
                                    st.write(f"**Address:** {result.get('address', 'N/A')}")
                                    st.write(f"**Phone:** {result.get('phone', 'N/A')}")
                            else:
                                st.info("Provider not found in NPPES")
                
                # EDI Generation
                st.header("📄 X12 837P EDI Output")
                edi_output = cms1500_to_edi837p(cms1500)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"✅ **EDI Generated ({len(edi_output)} chars)**")
                with col2:
                    st.write(f"**Claim:** {form_data.get('claim_number', 'N/A')}")
                
                # Display EDI
                with st.expander("View Full EDI"):
                    st.code(edi_output, language="text")
                
                # Downloads
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.download_button(
                        label="📥 Download .837",
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
                    if st.button("🔄 Submit Another", use_container_width=True):
                        st.rerun()
            
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.exception(e)
    else:
        st.info("CMS-1500 form not available. Check installation.")

elif st.session_state.mode == 'form':
    st.header("📝 Guided Form Entry")
    if render_form_mode is not None:
        render_form_mode()
    else:
        st.info("Form mode not available.")

elif st.session_state.mode == 'text':
    st.header("📄 Natural Language Entry")
    if render_text_mode is not None:
        render_text_mode()
    else:
        st.info("Text mode not available.")

elif st.session_state.mode == 'edi':
    st.header("📊 EDI File Parser")
    if render_edi_mode is not None:
        render_edi_mode()
    else:
        # Fallback EDI upload
        st.subheader("Upload 837 EDI File")
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['txt', 'edi', '837']
        )
        
        if uploaded_file is not None:
            if st.button("🚀 Process File"):
                file_content = uploaded_file.read().decode('utf-8')
                parsed_data = parse_uploaded_file(file_content, uploaded_file.name)
                if parsed_data:
                    st.session_state.parsed_claims = parsed_data
                    st.session_state.file_name = uploaded_file.name
                    st.session_state.file_uploaded = True
                    validation_results = validate_claims(parsed_data)
                    if validation_results:
                        st.session_state.validation_results = validation_results
                        analytics_data = generate_analytics(parsed_data, validation_results)
                        if analytics_data:
                            st.session_state.analytics_data = analytics_data
                            st.success("✅ File processed! See Analytics tab for results.")
                            st.balloons()

elif st.session_state.mode == 'analytics':
    st.header("📈 Claims Analytics")
    
    if st.session_state.file_uploaded and st.session_state.analytics_data:
        analytics = st.session_state.analytics_data
        
        # Overview metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Claims", analytics.get('total_claims', 0))
        with col2:
            st.metric("Total Amount", f"${analytics.get('total_claim_amount', 0):,.2f}")
        with col3:
            st.metric("Average", f"${analytics.get('average_claim_amount', 0):,.2f}")
        with col4:
            denial_risk = analytics.get('high_denial_risk_count', 0)
            st.metric("High Risk", denial_risk)
        
        st.divider()
        
        # Charts
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("💰 Claim Amounts")
            if 'claim_amounts' in analytics and len(analytics['claim_amounts']) > 0:
                df = pd.DataFrame({
                    'Claim': analytics.get('claim_ids', []),
                    'Amount': analytics['claim_amounts']
                })
                st.bar_chart(df.set_index('Claim') if len(df) > 0 else None)
        
        with col2:
            st.subheader("🏥 Service Types")
            if 'service_types' in analytics and analytics['service_types']:
                df = pd.DataFrame.from_dict(
                    analytics['service_types'],
                    orient='index',
                    columns=['Count']
                )
                st.bar_chart(df)
    else:
        st.info("👆 Upload and process a file in the EDI Parser tab to see analytics.")


# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #999; font-size: 0.9rem;">
    OptiClaimAI v3.0 | X12 837P Compliant | Streamlit Cloud Ready
</div>
""", unsafe_allow_html=True)
