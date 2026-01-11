"""
EDI file upload and processing component
"""

import streamlit as st
from model.claim_builder import ClaimBuilder
from engine.rules_engine_v2 import ClaimRulesEngine
from streamlit_ui.results_display import render_results


def render_edi_mode():
    """Render EDI 837 file upload and processing"""
    
    st.header("⬆️ Upload EDI 837 File")
    st.info("Upload a standard 837 Professional (837P) EDI file for advanced processing.")
    
    uploaded_file = st.file_uploader(
        "Upload 837 EDI File",
        type=['txt', 'edi', '837'],
        help="Upload an EDI 837 Professional format file"
    )
    
    if uploaded_file is not None:
        try:
            file_content = uploaded_file.read().decode('utf-8')
            
            if st.button("🔍 Process EDI File", type="primary", use_container_width=True):
                with st.spinner("Processing EDI file..."):
                    # Build claim from EDI
                    claim = ClaimBuilder.from_edi(file_content)
                    
                    if claim:
                        # Validate
                        engine = ClaimRulesEngine()
                        validation = engine.validate(claim)
                        
                        st.session_state.claim = claim
                        st.session_state.validation_result = validation
                        
                        render_results(claim, validation)
                    else:
                        st.error("❌ Could not parse EDI file. Please check format and try again.")
        
        except Exception as e:
            st.error(f"❌ Error processing file: {e}")
