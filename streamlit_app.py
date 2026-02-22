"""
OptiClaimAI - Redesigned UI with Google-like Search Interface
Main App - Completely new layout and navigation structure
"""

import streamlit as st
import pandas as pd
import json
from typing import Dict, List, Optional
import sys
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent))

# Core imports
from engine.parser import EDI837Parser
from engine.validator import ClaimValidator
from engine.analytics import ClaimsAnalytics
from engine.ollama_wrapper import get_ollama
from engine.nppes_lookup import get_nppes_lookup
from engine.edi_837p_generator import cms1500_to_edi837p

# UI imports
try:
    from streamlit_ui.cms1500_form_v3 import render_cms1500_form
    from streamlit_ui.results_display import render_results
except ImportError:
    render_cms1500_form = None
    render_results = None

# Page config
st.set_page_config(
    page_title="OptiClaimAI - Healthcare Claims Intelligence",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Google-like interface
st.markdown("""
<style>
/* Global Styles */
* {
    margin: 0;
    padding: 0;
}

/* Hide default sidebar */
[data-testid="collapsedControl"] {
    display: none;
}

/* Top Navigation Bar */
.top-nav {
    background: white;
    padding: 12px 20px;
    border-bottom: 1px solid #e0e0e0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: sticky;
    top: 0;
    z-index: 100;
}

.nav-logo {
    font-size: 24px;
    font-weight: bold;
    color: #1f77b4;
}

.nav-links {
    display: flex;
    gap: 20px;
    list-style: none;
}

.nav-links a {
    color: #5f6368;
    text-decoration: none;
    font-size: 14px;
    transition: color 0.2s;
}

.nav-links a:hover {
    color: #202124;
}

/* Main Container */
.main-container {
    display: flex;
    height: 100vh;
    transition: all 0.3s ease;
}

/* Left Sidebar - Chat History */
.chat-sidebar {
    width: 280px;
    background: #f9f9f9;
    border-right: 1px solid #e0e0e0;
    padding: 16px;
    overflow-y: auto;
    transition: width 0.3s ease;
}

.chat-sidebar.collapsed {
    width: 0;
    padding: 0;
    border: none;
}

.sidebar-header {
    font-weight: 600;
    color: #202124;
    margin-bottom: 12px;
    font-size: 14px;
}

.chat-history-item {
    padding: 8px;
    margin: 4px 0;
    background: white;
    border-radius: 8px;
    cursor: pointer;
    font-size: 13px;
    color: #5f6368;
    border-left: 3px solid transparent;
    transition: all 0.2s;
}

.chat-history-item:hover {
    background: #ececec;
    border-left-color: #1f77b4;
}

/* Center Content Area */
.content-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
}

.search-section {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 40px 20px;
    text-align: center;
}

.search-box-container {
    width: 100%;
    max-width: 600px;
}

.search-header {
    font-size: 32px;
    font-weight: 300;
    color: #202124;
    margin-bottom: 24px;
}

.search-box {
    display: flex;
    gap: 12px;
    align-items: center;
    background: white;
    border: 1px solid #dadce0;
    border-radius: 24px;
    padding: 10px 20px;
    box-shadow: 0 1px 1px rgba(0,0,0,0.08);
    transition: all 0.2s;
}

.search-box:hover {
    box-shadow: 0 1px 6px rgba(32,33,36,0.11);
}

.search-box input {
    flex: 1;
    border: none;
    outline: none;
    font-size: 16px;
    padding: 0;
}

.search-buttons {
    display: flex;
    gap: 12px;
    justify-content: center;
    margin-top: 20px;
}

.search-btn {
    padding: 10px 24px;
    background: #f8f9fa;
    border: 1px solid #f8f9fa;
    border-radius: 4px;
    color: #3c4043;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.2s;
}

.search-btn:hover {
    border-color: #dadce0;
    box-shadow: 0 1px 1px rgba(0,0,0,0.1);
}

/* Model Selector */
.model-selector {
    display: flex;
    gap: 8px;
    justify-content: center;
    margin-bottom: 12px;
    flex-wrap: wrap;
}

.model-btn {
    padding: 6px 12px;
    background: white;
    border: 1px solid #dadce0;
    border-radius: 16px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
}

.model-btn:hover {
    border-color: #1f77b4;
    color: #1f77b4;
}

.model-btn.active {
    background: #1f77b4;
    color: white;
    border-color: #1f77b4;
}

/* Results Area */
.results-container {
    padding: 20px 40px;
    max-width: 800px;
    margin: 0 auto;
}

.result-card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 20px;
    margin: 12px 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.result-title {
    font-size: 18px;
    font-weight: 500;
    color: #202124;
    margin-bottom: 12px;
}

.result-summary {
    font-size: 14px;
    color: #5f6368;
    line-height: 1.6;
    margin-bottom: 12px;
}

.result-actions {
    display: flex;
    gap: 12px;
    margin-top: 12px;
}

.action-btn {
    padding: 8px 16px;
    background: #f8f9fa;
    border: 1px solid #dadce0;
    border-radius: 4px;
    color: #1f77b4;
    cursor: pointer;
    font-size: 13px;
    transition: all 0.2s;
}

.action-btn:hover {
    background: #1f77b4;
    color: white;
}

/* Analytics Container */
.analytics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
    margin: 20px 0;
}

.metric-card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
}

.metric-value {
    font-size: 32px;
    font-weight: bold;
    color: #1f77b4;
}

.metric-label {
    font-size: 14px;
    color: #5f6368;
    margin-top: 8px;
}

/* Smooth Transitions */
.fade-in {
    animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

.slide-in {
    animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
    from { transform: translateX(-20px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session():
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'search'
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = 'llama3.1'
    if 'search_query' not in st.session_state:
        st.session_state.search_query = ''
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'sidebar_open' not in st.session_state:
        st.session_state.sidebar_open = False

init_session()

# ============= TOP NAVIGATION =============

col_nav = st.columns([0.2, 0.6, 0.2])

with col_nav[0]:
    st.markdown("### 🏥 OptiClaimAI")

with col_nav[1]:
    pass

with col_nav[2]:
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("📊 Analytics", key="nav_analytics", use_container_width=True):
            st.session_state.current_page = 'analytics'
            st.rerun()
    with c2:
        if st.button("📋 Forms", key="nav_forms", use_container_width=True):
            st.session_state.current_page = 'forms'
            st.rerun()
    with c3:
        if st.button("☰ Menu", key="nav_menu", use_container_width=True):
            st.session_state.sidebar_open = not st.session_state.sidebar_open
            st.rerun()

st.divider()

# ============= MAIN CONTENT AREA =============

if st.session_state.current_page == 'search':
    # Google-like search interface
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        st.markdown("### OptiClaimAI")
        st.markdown("*Healthcare Claims Intelligence*")
        st.write("")
        
        # Model selector
        st.markdown("**Select AI Model:**")
        model_cols = st.columns(3)
        ollama = get_ollama()
        available_models = ollama.list_models() if ollama.is_available() else ['llama3.1']
        
        for idx, model in enumerate(available_models):
            with model_cols[idx % 3]:
                if st.button(
                    f"{'✓ ' if model == st.session_state.selected_model else ''}{model}",
                    key=f"model_{model}",
                    use_container_width=True
                ):
                    st.session_state.selected_model = model
                    st.rerun()
        
        st.write("")
        
        # Search/Query input
        query = st.text_input(
            "Search or ask about claims, EDI, or upload data:",
            placeholder="e.g., 'Parse EDI file', 'Analyze claim rejection', 'Show claim analytics'",
            label_visibility="collapsed"
        )
        
        if query:
            st.session_state.search_query = query
        
        # Search buttons
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            process = st.button("🔍 Process", use_container_width=True)
        with col_btn2:
            upload = st.button("📤 Upload File", use_container_width=True)
        with col_btn3:
            chat = st.button("💬 Chat", use_container_width=True)
        
        if process and query:
            st.session_state.current_page = 'processing'
            st.rerun()
        elif upload:
            st.session_state.current_page = 'upload'
            st.rerun()
        elif chat:
            st.session_state.current_page = 'chat'
            st.rerun()

elif st.session_state.current_page == 'processing':
    st.markdown("## Processing Your Request")
    st.markdown(f"**Query:** {st.session_state.search_query}")
    st.write("")
    
    # Process based on query
    query = st.session_state.search_query.lower()
    
    if 'edi' in query or '837' in query or 'parse' in query:
        st.info("📄 EDI Parser Mode")
        uploaded_file = st.file_uploader("Upload EDI file", type=['txt', 'edi', '837'])
        
        if uploaded_file:
            file_content = uploaded_file.read().decode('utf-8')
            
            with st.spinner("Parsing EDI file..."):
                try:
                    parser = EDI837Parser()
                    parsed_data = parser.parse(file_content)
                    
                    if parsed_data and parsed_data.get('claims'):
                        st.success("✅ EDI parsed successfully")
                        
                        # Show parsed claims
                        st.markdown("### Claims Found")
                        claims = parsed_data.get('claims', [])
                        st.write(f"**Total Claims: {len(claims)}**")
                        
                        # Immediately validate
                        with st.spinner("Validating claims..."):
                            validator = ClaimValidator()
                            validation_results = validator.validate_all(parsed_data)
                            
                            if validation_results:
                                st.session_state.results = {
                                    'type': 'validation',
                                    'data': validation_results,
                                    'parsed': parsed_data
                                }
                                
                                # Show validation summary
                                total_errors = sum(len(v.get('errors', [])) for v in validation_results if v)
                                total_warnings = sum(len(v.get('warnings', [])) for v in validation_results if v)
                                valid_claims = len([v for v in validation_results if v and len(v.get('errors', [])) == 0])
                                
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Total Errors", total_errors)
                                with col2:
                                    st.metric("Total Warnings", total_warnings)
                                with col3:
                                    st.metric("Valid Claims", valid_claims)
                                
                                st.write("")
                                st.success("✅ Validation complete! Go to Analytics to see detailed results.")
                                
                                # Auto-navigate
                                if st.button("📊 View Analytics"):
                                    st.session_state.current_page = 'analytics'
                                    st.rerun()
                            else:
                                st.error("Validation failed - no results returned")
                                # FIX APPLIED: Clear results on failure to prevent errors on other pages
                                st.session_state.results = None
                    else:
                        st.error("No claims found in EDI file")
                        # FIX APPLIED: Clear results on failure
                        st.session_state.results = None
                
                except Exception as e:
                    st.error(f"Error parsing file: {str(e)}")
                    st.write("Make sure the file is a valid EDI 837P format")
                    # FIX APPLIED: Clear results on exception
                    st.session_state.results = None
    
    elif 'claim' in query or 'form' in query or 'cms' in query:
        st.info("📋 CMS-1500 Form Mode")
        if render_cms1500_form:
            form_data = render_cms1500_form()
            
            if form_data:
                st.success("✅ Form submitted")
                st.session_state.results = {
                    'type': 'form',
                    'data': form_data
                }
            else:
                # FIX APPLIED: Handle case where form data is empty or invalid
                st.info("Form data is empty or incomplete. Please fill out the required fields.")
                # FIX APPLIED: Clear results on failure
                st.session_state.results = None
        else:
            st.error("CMS-1500 form component is not available.")
    
    elif 'analytics' in query:
        st.session_state.current_page = 'analytics'
        st.rerun()
    
    if st.button("← Back"):
        st.session_state.current_page = 'search'
        st.rerun()

elif st.session_state.current_page == 'chat':
    st.markdown("## 💬 Chat with AI")
    
    # Chat display
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            if msg['role'] == 'user':
                with st.chat_message("user"):
                    st.write(msg['content'])
            else:
                with st.chat_message("assistant"):
                    st.write(msg['content'])
    
    # Chat input
    user_input = st.chat_input("Ask me anything about healthcare claims...")
    
    if user_input:
        st.session_state.chat_history.append({
            'role': 'user',
            'content': user_input
        })
        
        with st.spinner("Thinking..."):
            ollama = get_ollama()
            if ollama.is_available():
                # Build context from rules and code_sets
                context = """You are an expert healthcare claims analyst. 
You have access to:
- X12 837P EDI standards
- CMS-1500 form requirements
- HIPAA compliance rules
- Medical coding standards (CPT, ICD-10, HCPCS)
- Common claim rejection reasons

Provide clear, actionable advice."""
                
                response = ollama.generate(
                    prompt=f"{context}\n\nUser: {user_input}",
                    model=st.session_state.selected_model
                )
                
                if response:
                    st.session_state.chat_history.append({
                        'role': 'assistant',
                        'content': response
                    })
                    st.rerun()

elif st.session_state.current_page == 'analytics':
    st.markdown("## 📊 Analytics & Insights")
    
    if not st.session_state.results:
        st.info("No results to analyze yet. Please process a claim file first.")
        if st.button("← Back to Home"):
            st.session_state.current_page = 'search'
            st.rerun()
    else:
        results_data = st.session_state.results
        
        if results_data['type'] == 'validation' and results_data.get('data'):
            st.markdown("### Claims Validation Analytics")
            
            validation_results = results_data['data']
            # This check is already good, but we ensure it's not None
            if not validation_results:
                st.warning("No validation results available to display.")
                # FIX APPLIED: It's safer to clear results if they are empty but not None
                # st.session_state.results = None # Uncomment if you want to clear it
                if st.button("← Back to Home"):
                    st.session_state.current_page = 'search'
                    st.rerun()
            else:
                # Metrics
                col1, col2, col3, col4 = st.columns(4)
                
                valid_results = [v for v in validation_results if v]
                total_claims = len(valid_results)
                
                with col1:
                    st.metric("Total Claims", total_claims)
                with col2:
                    total_errors = sum(len(v.get('errors', [])) for v in valid_results if v)
                    st.metric("Total Errors", total_errors)
                with col3:
                    total_warnings = sum(len(v.get('warnings', [])) for v in valid_results if v)
                    st.metric("Warnings", total_warnings)
                with col4:
                    valid = len([v for v in valid_results if v and len(v.get('errors', [])) == 0])
                    st.metric("Valid", valid)
                
                st.write("")
                
                # AI-Powered Insights
                if st.button("🤖 Get AI Insights"):
                    with st.spinner("Analyzing with AI..."):
                        ollama = get_ollama()
                        if ollama.is_available():
                            total_errors = sum(len(v.get('errors', [])) for v in validation_results if v)
                            total_warnings = sum(len(v.get('warnings', [])) for v in validation_results if v)
                            
                            prompt = f"""Analyze these healthcare claims validation results and provide:

1. **Key Issues Summary**: Top 3 validation problems found
2. **Rejection Risk**: Which claims are likely to be rejected and why
3. **Optimization Tips**: How to fix the most common errors
4. **Compliance Notes**: HIPAA and X12 compliance insights

Validation Summary:
- Total Claims: {total_claims}
- Claims with Errors: {len([v for v in validation_results if v and len(v.get('errors', [])) > 0])}
- Total Error Count: {total_errors}
- Total Warnings: {total_warnings}

Provide actionable insights that a medical biller should know."""
                            
                            response = ollama.generate(
                                prompt=prompt,
                                model=st.session_state.selected_model,
                                temperature=0.7
                            )
                            
                            if response:
                                st.markdown("### AI Analysis")
                                st.markdown(response)
                        else:
                            st.warning("AI service not available. Showing rule-based analysis only.")
                
                # Detailed Issues
                st.markdown("### Issue Breakdown")
                
                all_errors = {}
                for result in validation_results:
                    if result:
                        for error in result.get('errors', []):
                             if isinstance(error, dict):
                                 error_type = error.get('type', 'Unknown')
                             else:
                                 error_type = 'An unexpected error occurred'
                                 all_errors[error_type] = all_errors.get(error_type, 0) + 1
                
                if all_errors:
                    df = pd.DataFrame(list(all_errors.items()), columns=['Error Type', 'Count'])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.bar_chart(df.set_index('Error Type'))
                    with col2:
                        st.subheader("Error Summary")
                        for error_type, count in sorted(all_errors.items(), key=lambda x: x[1], reverse=True):
                            st.write(f"• **{error_type}**: {count} occurrences")
                else:
                    st.success("✅ No errors found!")
                
                st.write("")
                if st.button("← Back"):
                    st.session_state.current_page = 'search'
                    st.rerun()

elif st.session_state.current_page == 'upload':
    st.markdown("## 📤 Upload & Process")
    
    uploaded_file = st.file_uploader("Choose file", type=['txt', 'edi', '837', 'json'])
    
    if uploaded_file:
        file_content = uploaded_file.read().decode('utf-8')
        
        if st.button("Process File", use_container_width=True):
            with st.spinner("Processing..."):
                try:
                    if uploaded_file.name.endswith(('.edi', '.837', '.txt')):
                        parser = EDI837Parser()
                        parsed_data = parser.parse(file_content)
                        
                        if parsed_data and parsed_data.get('claims'):
                            # Validate claims
                            validator = ClaimValidator()
                            validation_results = validator.validate_all(parsed_data)
                            
                            st.session_state.results = {
                                'type': 'validation',
                                'data': validation_results,
                                'parsed': parsed_data
                            }
                            st.success("✅ File processed successfully!")
                            st.session_state.current_page = 'analytics'
                            st.rerun()
                        else:
                            st.error("No valid claims found in file")
                            # FIX APPLIED: Clear results on failure
                            st.session_state.results = None
                    else:
                        st.error("Unsupported file format")
                        # FIX APPLIED: Clear results on failure
                        st.session_state.results = None
                except Exception as e:
                    st.error(f"Error processing file: {str(e)}")
                    # FIX APPLIED: Clear results on exception
                    st.session_state.results = None
    
    if st.button("← Back"):
        st.session_state.current_page = 'search'
        st.rerun()

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #999; font-size: 12px;">
OptiClaimAI v5 - Redesigned | Healthcare Claims Intelligence Platform
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# END OF SCRIPT
# ==============================================================================

# INSTRUCTIONS:
# The original error you encountered was happening AFTER this point in the script.
# You likely have some extra code at the very bottom of your file that is not
# shown here.
#
# To fix the error completely:
# 1. Save this corrected version of the file.
# 2. Open your `streamlit_app_v5.py` file.
# 3. SCROLL TO THE VERY BOTTOM, past the footer and the comments above.
# 4. DELETE any code you find below the "END OF SCRIPT" comments.
#
# If you had a line like `error_type = error.get(...)`, replace it with the
# safe pattern below to prevent it from crashing again:
#
#   if isinstance(error, dict):
#       error_type = error.get('type', 'Unknown')
#   else:
#       error_type = 'An unexpected error occurred'
#
# This file is now much more robust and should not crash from state issues.
