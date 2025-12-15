import streamlit as st
import json
from pathlib import Path
from engine.parser import parse_837
from engine.model import predict_denial

st.set_page_config(page_title='OptiClaimAI', layout='centered')

# Disclaimer banner
st.error("⚠ OptiClaimAI is a pre-submission QA and analytics tool. Files are processed in-session only and are not stored. Do not upload live production PHI. This tool is not a clearinghouse or adjudication system.")

st.title('OptiClaimAI — AI Claims Scrubber')

st.markdown('Upload a synthetic 837 file and run validation.')

uploaded = st.file_uploader('Upload 837 file', type=['txt','837'])
use_ollama = st.checkbox('Use Ollama (local)', value=False)

result = None
if st.button('Predict from sample1'):
    sample_path = Path('data/sample_837/sample1.837')
    if sample_path.exists():
        raw = sample_path.read_text(encoding='utf-8')
        parsed = parse_837(raw)
        if 'error' in parsed:
            st.error(f"Parsing failed: {parsed['error']}")
        else:
            result = predict_denial(raw, parsed, use_ollama=use_ollama)
    else:
        st.error('sample1.837 not found.')

if uploaded and st.button('Predict uploaded'):
    raw = uploaded.getvalue().decode('utf-8', errors='ignore')
    parsed = parse_837(raw)
    if 'error' in parsed:
        st.error(f"Parsing failed: {parsed['error']}")
    else:
        result = predict_denial(raw, parsed, use_ollama=use_ollama)

if result:
    # Mask PHI
    if 'patient' in parsed:
        parsed['patient'] = {k: '***MASKED***' if 'name' in k.lower() or 'id' in k.lower() else v for k, v in parsed['patient'].items()}
    
    # Summary Section
    st.header('Summary Metrics')
    summary = result['summary']
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric('Total Claims', summary['total_claims'])
        st.metric('Invalid Claims', summary['invalid_claims'])
    with col2:
        st.metric('Invalid Percentage', f"{summary['invalid_percentage']}%")
        st.metric('High Risk Issues', summary['high_risk_issues'])
    with col3:
        st.metric('Estimated Rework Cost', f"${summary['estimated_rework_cost']}")
    
    # Claim Type Section
    st.header('Claim Type Detection')
    st.write(f"**Detected Type:** {result['claim_type']}")
    st.write(f"**Reasoning:** {result['claim_reason']}")
    
    if result['dhcs_applied']:
        st.info("California DHCS Rules Applied")
    
    # Detailed Issues Section
    st.header('Detailed Confirmed Issues')
    issues = result['issues']
    if issues:
        for issue in issues:
            with st.expander(f"{issue['issue_type']} ({issue['severity']} Severity)"):
                st.write(f"**Why Failed:** {issue['why_failed']}")
                st.write(f"**What to Fix:** {issue['what_to_fix']}")
                st.write(f"**Reference:** {issue['reference']}")
    else:
        st.success("No issues detected. Claim appears valid.")

st.markdown('---')
st.markdown('**Samples included:** `data/sample_837/*.837`')
st.markdown('**To enable Ollama:** make sure Ollama daemon is running and you have pulled a model like `llama3.1`.')
