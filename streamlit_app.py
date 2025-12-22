import streamlit as st
import json
from pathlib import Path
from engine.parser import parse_837
from engine.model import predict_denial
from engine.llm import explain_issue, call_ollama

st.set_page_config(
    page_title='OptiClaimAI',
    layout='centered',
    page_icon='🧠'
)

# Initialize session state
if 'results' not in st.session_state:
    st.session_state.results = None
    st.session_state.claim_type = None
    st.session_state.summary_metrics = None
    st.session_state.parsed = None
    st.session_state.raw = None
    st.session_state.explanations = {}
    st.session_state.followups = {}

# Disclaimer banner
st.error("⚠ OptiClaimAI is a pre-submission QA and analytics tool. Files are processed in-session only and are not stored. Do not upload live production PHI. This tool is not a clearinghouse or adjudication system.")

st.title('OptiClaimAI — AI Claims Scrubber')

st.markdown('Upload a synthetic 837 file and run validation.')

uploaded = st.file_uploader('Upload 837 file', type=['txt','837'])

col1, col2, col3 = st.columns(3)
with col1:
    if st.button('Predict from sample1'):
        with st.spinner('Processing sample file...'):
            sample_path = Path('data/sample_837/sample1.837')
            if sample_path.exists():
                raw = sample_path.read_text(encoding='utf-8')
                parsed = parse_837(raw)
                if 'error' not in parsed:
                    st.session_state.results = predict_denial(raw, parsed)
                    st.session_state.claim_type = st.session_state.results['claim_type']
                    st.session_state.summary_metrics = st.session_state.results['summary']
                    st.session_state.parsed = parsed
                    st.session_state.raw = raw
                else:
                    st.error(f"Parsing failed: {parsed['error']}")
            else:
                st.error('sample1.837 not found.')
with col2:
    if st.button('Predict from sample2'):
        with st.spinner('Processing sample file...'):
            sample_path = Path('data/sample_837/sample2.837')
            if sample_path.exists():
                raw = sample_path.read_text(encoding='utf-8')
                parsed = parse_837(raw)
                if 'error' not in parsed:
                    st.session_state.results = predict_denial(raw, parsed)
                    st.session_state.claim_type = st.session_state.results['claim_type']
                    st.session_state.summary_metrics = st.session_state.results['summary']
                    st.session_state.parsed = parsed
                    st.session_state.raw = raw
                else:
                    st.error(f"Parsing failed: {parsed['error']}")
            else:
                st.error('sample2.837 not found.')
with col3:
    if st.button('Clear Results'):
        st.session_state.results = None
        st.session_state.claim_type = None
        st.session_state.summary_metrics = None
        st.session_state.parsed = None
        st.session_state.raw = None
        st.session_state.explanations = {}
        st.session_state.followups = {}
        st.success('Results cleared. Upload a new file or select a sample.')

if uploaded and st.button('Run Analysis on Uploaded'):
        with st.spinner('Processing uploaded file...'):
            raw = uploaded.getvalue().decode('utf-8', errors='ignore')
            parsed = parse_837(raw)
            if 'error' not in parsed:
                st.session_state.results = predict_denial(raw, parsed)
                st.session_state.claim_type = st.session_state.results['claim_type']
                st.session_state.summary_metrics = st.session_state.results['summary']
                st.session_state.parsed = parsed
                st.session_state.raw = raw
            else:
                st.error(f"Parsing failed: {parsed['error']}")

if st.session_state.results:
    # Mask PHI
    if 'patient' in st.session_state.parsed:
        st.session_state.parsed['patient'] = {k: '***MASKED***' if 'name' in k.lower() or 'id' in k.lower() else v for k, v in st.session_state.parsed['patient'].items()}
    
    # Summary Section
    st.header('Summary Metrics')
    summary = st.session_state.summary_metrics
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
    st.write(f"**Detected Type:** {st.session_state.claim_type}")
    st.write(f"**Reasoning:** {st.session_state.results['claim_reason']}")
    
    if st.session_state.results['dhcs_applied']:
        st.info("California DHCS Rules Applied")
    
    # Detailed Issues Section
    st.header('Detailed Confirmed Issues')
    issues = st.session_state.results['issues']
    if issues:
        for issue in issues:
            with st.expander(f"{issue['issue_type']} ({issue['severity']} Severity)"):
                st.write(f"**Why Failed:** {issue['why_failed']}")
                st.write(f"**What to Fix:** {issue['what_to_fix']}")
                st.write(f"**Reference:** {issue['reference']}")
                
                # AI Explanation Button
                if st.button(f"Explain with AI", key=f"explain_{issue['issue_type']}"):
                    with st.spinner("Generating AI explanation..."):
                        explanation = explain_issue(issue, st.session_state.parsed, st.session_state.raw)
                        st.session_state.explanations[issue['issue_type']] = explanation
                        st.rerun()  # To update the UI immediately
                
                # Display AI Explanation if available
                if issue['issue_type'] in st.session_state.explanations:
                    st.write("**AI Explanation:**")
                    st.write(st.session_state.explanations[issue['issue_type']])
                    
                    # Follow-up Question
                    followup_question = st.text_input(
                        f"Ask a follow-up question about this issue",
                        key=f"followup_input_{issue['issue_type']}"
                    )
                    if st.button(f"Submit Follow-up", key=f"submit_followup_{issue['issue_type']}"):
                        if followup_question.strip():
                            prompt = f"""
Previous AI Explanation: {st.session_state.explanations[issue['issue_type']]}

Follow-up Question: {followup_question}

As a US Healthcare EDI Expert, provide a clear answer to this follow-up question, referencing TR3 standards, loops, segments, and payer rules where applicable.
"""
                            followup_answer = call_ollama(prompt)
                            if issue['issue_type'] not in st.session_state.followups:
                                st.session_state.followups[issue['issue_type']] = []
                            st.session_state.followups[issue['issue_type']].append({
                                'question': followup_question,
                                'answer': followup_answer
                            })
                            st.rerun()  # Update UI
                    
                    # Display Follow-ups
                    if issue['issue_type'] in st.session_state.followups:
                        st.write("**Follow-up Q&A:**")
                        for fu in st.session_state.followups[issue['issue_type']]:
                            st.write(f"**Q:** {fu['question']}")
                            st.write(f"**A:** {fu['answer']}")
                            st.markdown("---")
    else:
        st.success("No issues detected. Claim appears valid.")

st.markdown('---')
st.markdown('**Samples included:** `data/sample_837/*.837`')
st.markdown('**AI Explanations:** Powered by local Ollama (llama3.1). Ensure Ollama is running for AI features.')

with st.expander("🔐 Security & Privacy"):
    st.markdown("""
    • Files processed **in-memory only**  
    • No uploads stored  
    • AI explanations generated locally via Ollama (no external APIs)  
    • Deterministic rule engine  
    • Explainable outputs (no black-box scoring)
    """)
