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

col1, col2 = st.columns(2)
with col1:
    if st.button('Predict from sample1'):
        sample_path = Path('data/sample_837/sample1.837')
        if sample_path.exists():
            raw = sample_path.read_text(encoding='utf-8')
            parsed = parse_837(raw)
            result = predict_denial(raw, parsed, use_ollama=use_ollama)
            # Mask PHI
            if 'patient' in parsed:
                parsed['patient'] = {k: '***MASKED***' if 'name' in k.lower() or 'id' in k.lower() else v for k, v in parsed['patient'].items()}
            st.json(result)
        else:
            st.error('sample1.837 not found.')
with col2:
    if uploaded and st.button('Predict uploaded'):
        raw = uploaded.getvalue().decode('utf-8', errors='ignore')
        parsed = parse_837(raw)
        result = predict_denial(raw, parsed, use_ollama=use_ollama)
        # Mask PHI
        if 'patient' in parsed:
            parsed['patient'] = {k: '***MASKED***' if 'name' in k.lower() or 'id' in k.lower() else v for k, v in parsed['patient'].items()}
        st.json(result)

st.markdown('---')
st.markdown('**Samples included:** `data/sample_837/*.837`')
st.markdown('**To enable Ollama:** make sure Ollama daemon is running and you have pulled a model like `llama3.1`.')
