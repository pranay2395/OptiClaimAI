"""
Streamlit free-text claim input component
"""

import streamlit as st


def render_text_mode() -> str:
    """Render free-text claim entry"""
    
    st.header("📝 Describe Your Claim")
    st.info("""
    Tell us about the patient visit in plain language. Include:
    - Patient name and date of birth
    - Insurance ID
    - Provider name and NPI
    - Service date
    - Diagnosis codes (or descriptions)
    - Procedures and charges
    
    **Example:**
    > Patient Jane Doe, DOB 1985-03-15, Insurance Blue Cross #BC123456. 
    > Visit with Dr. John Smith (NPI 1234567890) on 2024-01-10. 
    > Chief complaint: lower back pain. Diagnosis: M54.5. 
    > Procedures: Office visit 99213 ($150), X-ray pelvis 71210 ($200).
    """)
    
    text_input = st.text_area(
        "Describe the claim",
        height=300,
        placeholder="Patient John Doe, DOB 1980-05-20, Insurance ID ABC123..."
    )
    
    col1, col2 = st.columns([1, 1])
    with col1:
        submitted = st.button("🔍 Parse & Validate", type="primary", use_container_width=True)
    with col2:
        st.button("🔄 Clear", use_container_width=True)
    
    if submitted and text_input.strip():
        return text_input.strip()
    
    return None
