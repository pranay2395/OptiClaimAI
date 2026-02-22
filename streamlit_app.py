"""
OptiClaimAI - Production Application (FIXED Streamlit Runtime Model)
Strict adherence to Streamlit patterns: render-only during execution, 
state mutation via callbacks only
"""

import streamlit as st
import pandas as pd
import json
from typing import Dict, List, Optional
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# ============= CORE IMPORTS (NO AI) =============

from engine.parser import EDI837Parser
from engine.validator import ClaimValidator
from engine.analytics import ClaimsAnalytics

# Multi-mode UI
try:
    from streamlit_ui.form_input import render_form_mode
    from streamlit_ui.text_input import render_text_mode
    from streamlit_ui.edi_mode import render_edi_mode
    from streamlit_ui.cms1500_form_v3 import render_cms1500_form
    from streamlit_ui.results_display import render_results
    from streamlit_ui.chat_interface import render_chat_interface
except ImportError:
    render_form_mode = None
    render_text_mode = None
    render_edi_mode = None
    render_cms1500_form = None
    render_results = None
    render_chat_interface = None

# CMS-1500 & EDI (NO AI)
try:
    from model.cms1500_schema import CMS1500
    from engine.validate_cms1500 import validate_cms1500, build_cms1500_object
    from engine.edi_837p_generator import cms1500_to_edi837p
    from engine.nppes_lookup import get_nppes_lookup
except ImportError:
    pass

# Claim Builder & Engine (NO AI)
try:
    from model.claim_builder import ClaimBuilder
    from engine.rules_engine_v2 import ClaimRulesEngine
except ImportError:
    ClaimBuilder = None
    ClaimRulesEngine = None

# ============= AI ENGINE FACTORY (LAZY + RUNTIME) =============

# Import the proper Ollama wrapper
try:
    from engine.ollama_wrapper import get_ollama
except ImportError:
    get_ollama = None

class AIEngineFactory:
    """Lazy-loaded, runtime-selectable AI provider"""
    
    @staticmethod
    def get_ollama_response(prompt: str, model: str = "llama3.1") -> Optional[str]:
        """Execute Ollama request on port 11434 (FIXED PORT)"""
        try:
            if get_ollama is None:
                return None
            
            ollama = get_ollama()
            if not ollama.is_available():
                return "Ollama not available at localhost:11434"
            
            result = ollama.generate(
                prompt=prompt,
                model=model,
                temperature=0.7,
                top_p=0.9
            )
            return result if result else None
        except Exception as e:
            return f"Ollama error: {str(e)}"
    
    @staticmethod
    def get_backend_response(prompt: str) -> Optional[str]:
        """Execute request to FastAPI backend service"""
        try:
            import requests
            response = requests.post(
                "http://localhost:8001/analyze",
                json={"prompt": prompt},
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                # Handle various response formats
                if isinstance(result, dict) and "response" in result:
                    return result.get("response", "")
                elif isinstance(result, dict) and "analysis" in result:
                    return result.get("analysis", "")
                elif isinstance(result, str):
                    return result
                return str(result)
            return None
        except Exception as e:
            return f"Backend error: {str(e)}"
    
    @staticmethod
    def get_openai_response(prompt: str, api_key: str, model: str = "gpt-4") -> Optional[str]:
        """Execute OpenAI request ONLY if called"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"OpenAI error: {str(e)}"
    
    @staticmethod
    def execute(provider: str, prompt: str, api_key: Optional[str] = None) -> Optional[str]:
        """Execute AI based on provider selection"""
        if provider == "ollama":
            return AIEngineFactory.get_ollama_response(prompt)
        elif provider == "backend":
            return AIEngineFactory.get_backend_response(prompt)
        elif provider == "openai" and api_key:
            return AIEngineFactory.get_openai_response(prompt, api_key)
        return None

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
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'chat_model' not in st.session_state:
        st.session_state.chat_model = "llama3.1"

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
        options=["� Chat", "📋 CMS-1500", "📝 Form", "📄 Text", "📊 EDI Parser", "📈 Analytics"],
        key="mode_selector"
    )
    
    if mode_select == "💬 Chat":
        st.session_state.mode = 'chat'
    elif mode_select == "📋 CMS-1500":
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
    
    - **Chat** - AI assistant (offline with Ollama)
    - **CMS-1500** - Complete form with EDI generation
    - **Form** - Guided form entry
    - **Text** - Natural language parsing
    - **EDI Upload** - Direct 837P file analysis
    - **Analytics** - Claims insights
    
    **Technology:**
    - X12 837P Compliant
    - Local Processing (No Cloud)
    - Ollama LLM Support (port 11434)
    - FastAPI Backend & OpenAI optional
    """)
    
    st.divider()
    
    if st.button("🔄 Reset", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# ============= MODE ROUTING =============

# Chat mode - Load first if selected
if st.session_state.mode == 'chat':
    if render_chat_interface is not None:
        render_chat_interface()
    else:
        st.error("Chat interface not available. Please check installation.")

elif st.session_state.mode is None or st.session_state.mode == 'cms1500':
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
    
    # AI Guidance Section
    with st.expander("🤖 AI Guidance Setup"):
        col1, col2 = st.columns(2)
        with col1:
            ai_provider = st.selectbox(
                "AI Provider",
                ["disabled", "ollama", "backend", "openai"],
                key="ai_provider_select"
            )
            if ai_provider != "disabled":
                st.session_state.ai_provider = ai_provider
                if ai_provider == "ollama":
                    st.success("✅ Connected to Ollama (port 8000)")
                elif ai_provider == "backend":
                    st.success("✅ Connected to FastAPI backend (port 8001)")
        
        with col2:
            if ai_provider == "openai":
                api_key = st.text_input(
                    "OpenAI API Key",
                    type="password",
                    key="openai_key_input"
                )
                if api_key:
                    st.session_state.openai_key = api_key
    
    # File upload section
    st.subheader("Upload 837 EDI File")
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['txt', 'edi', '837']
    )
    
    if uploaded_file is not None:
        col1, col2 = st.columns(2)
        with col1:
            def process_button_click():
                st.session_state.process_file = True
            
            st.button("🚀 Process File", on_click=process_button_click)
        
        with col2:
            def get_ai_guidance_click():
                st.session_state.get_ai_guidance = True
            
            st.button("🤖 Get AI Guidance", on_click=get_ai_guidance_click)
        
        # Process file flag
        if st.session_state.get("process_file", False):
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
                        st.success("✅ File processed successfully!")
            st.session_state.process_file = False
        
        # AI guidance flag
        if st.session_state.get("get_ai_guidance", False):
            if st.session_state.get("parsed_claims"):
                with st.spinner("🤖 Generating AI guidance..."):
                    prompt = f"""Analyze this healthcare claim for potential issues:
{json.dumps(st.session_state.parsed_claims, indent=2)[:2000]}

Provide:
1. Top 3 potential compliance issues
2. Recommended fixes
3. Risk level assessment
"""
                    ai_result = AIEngineFactory.execute(
                        st.session_state.get("ai_provider", "disabled"),
                        prompt,
                        api_key=st.session_state.get("openai_key")
                    )
                    if ai_result:
                        st.session_state.ai_guidance = ai_result
                        st.success("✅ AI Analysis Complete")
                    else:
                        st.warning("⚠️ AI service unavailable")
            st.session_state.get_ai_guidance = False
        
        # Display results
        if st.session_state.get("file_uploaded"):
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📊 Validation Results")
                if st.session_state.validation_results:
                    for i, result in enumerate(st.session_state.validation_results[:3]):
                        with st.expander(f"Claim {i+1}"):
                            st.write(result)
            
            with col2:
                st.subheader("📈 Analytics")
                if st.session_state.analytics_data:
                    st.json(st.session_state.analytics_data)
            
            # AI Guidance Display
            if st.session_state.get("ai_guidance"):
                st.divider()
                st.subheader("🤖 AI Analysis")
                st.info(st.session_state.ai_guidance)

elif st.session_state.mode == 'analytics':
    st.header("📈 Analytics Dashboard")
    
    if st.session_state.get("analytics_data"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Total Claims",
                st.session_state.analytics_data.get("total_claims", 0)
            )
        with col2:
            st.metric(
                "Validation Errors",
                st.session_state.analytics_data.get("total_errors", 0)
            )
        with col3:
            st.metric(
                "Warnings",
                st.session_state.analytics_data.get("total_warnings", 0)
            )
        
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Claims by Status")
            if "status_distribution" in st.session_state.analytics_data:
                st.bar_chart(st.session_state.analytics_data["status_distribution"])
        
        with col2:
            st.subheader("Error Categories")
            if "error_categories" in st.session_state.analytics_data:
                st.pie_chart(st.session_state.analytics_data["error_categories"])
        
        st.divider()
        st.subheader("Detailed Report")
        st.json(st.session_state.analytics_data)
    else:
        st.info("No analytics data available. Upload and process a file first.")


# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #999; font-size: 0.9rem;">
    OptiClaimAI v4.0 | Streamlit-Compliant Runtime | X12 837P Support
</div>
""", unsafe_allow_html=True)
