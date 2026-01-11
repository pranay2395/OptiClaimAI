"""
Streamlit form-based claim input component
"""

import streamlit as st
from datetime import datetime, date


def render_form_mode() -> dict:
    """Render guided step-by-step claim form"""
    
    st.header("📋 Enter Claim Details")
    st.info("Fill out the form below. Fields marked with * are required.")
    
    with st.form("claim_form", clear_on_submit=False):
        
        # Patient Information
        st.subheader("👤 Patient Information")
        col1, col2 = st.columns(2)
        with col1:
            patient_first = st.text_input("First Name *", key="patient_fn")
        with col2:
            patient_last = st.text_input("Last Name *", key="patient_ln")
        
        col1, col2 = st.columns(2)
        with col1:
            patient_dob = st.date_input("Date of Birth *", key="patient_dob", value=None)
        with col2:
            patient_gender = st.selectbox("Gender", ["Not specified", "M", "F", "Other"], key="patient_gender", index=0)
        
        col1, col2 = st.columns(2)
        with col1:
            insurance_id = st.text_input("Insurance ID / Member ID *", key="insurance_id")
        with col2:
            group_number = st.text_input("Group Number (optional)", key="group_number")
        
        col1, col2 = st.columns(2)
        with col1:
            patient_phone = st.text_input("Phone (optional)", key="patient_phone")
        with col2:
            patient_email = st.text_input("Email (optional)", key="patient_email")
        
        # Provider Information
        st.subheader("👨‍⚕️ Provider Information")
        col1, col2 = st.columns(2)
        with col1:
            provider_first = st.text_input("Provider First Name *", key="provider_fn")
        with col2:
            provider_last = st.text_input("Provider Last Name *", key="provider_ln")
        
        col1, col2 = st.columns(2)
        with col1:
            provider_npi = st.text_input("Provider NPI (10 digits) *", key="provider_npi", max_chars=10)
        with col2:
            provider_specialty = st.selectbox(
                "Specialty",
                ["Other", "Physical Therapy", "Mental Health", "Primary Care", "Cardiology", "Orthopedics"],
                key="provider_specialty"
            )
        
        provider_phone = st.text_input("Provider Phone (optional)", key="provider_phone")
        
        # Claim Information
        st.subheader("📅 Service Information")
        col1, col2 = st.columns(2)
        with col1:
            service_date = st.date_input("Service Date *", key="service_date", value=None)
        with col2:
            place_of_service = st.selectbox(
                "Place of Service *",
                ["11 - Office", "21 - Inpatient Hospital", "20 - Urgent Care", "12 - Home"],
                key="place_of_service",
                index=0
            )
        
        # Diagnoses
        st.subheader("🏥 Diagnoses (ICD-10)")
        st.caption("Enter up to 3 diagnosis codes (e.g., M54.5 for lower back pain)")
        
        diagnoses = []
        for i in range(3):
            col1, col2 = st.columns([1, 3])
            with col1:
                diag_code = st.text_input(f"Code {i+1}", key=f"diag_code_{i}", max_chars=7)
            with col2:
                diag_desc = st.text_input(f"Description {i+1}", key=f"diag_desc_{i}")
            
            if diag_code:
                diagnoses.append({'code': diag_code.upper(), 'description': diag_desc or None})
        
        # Procedures
        st.subheader("💊 Procedures (CPT Codes)")
        st.caption("Add the procedures performed and their charges")
        
        procedures = []
        max_procs = 5
        
        for i in range(max_procs):
            col1, col2, col3 = st.columns([2, 1.5, 1.5])
            with col1:
                proc_code = st.text_input(f"Procedure Code {i+1} (CPT)", key=f"proc_code_{i}", max_chars=5)
            with col2:
                proc_units = st.number_input(f"Units {i+1}", min_value=0.0, step=0.5, key=f"proc_units_{i}", value=1.0)
            with col3:
                proc_charge = st.number_input(f"Charge $ {i+1}", min_value=0.0, step=0.01, key=f"proc_charge_{i}")
            
            if proc_code and proc_charge > 0:
                procedures.append({
                    'code': proc_code.upper(),
                    'units': proc_units,
                    'charge': proc_charge
                })
        
        st.divider()
        submitted = st.form_submit_button("🔍 Validate Claim", type="primary", use_container_width=True)
    
    if submitted:
        # Validation
        errors = []
        if not patient_first:
            errors.append("Patient first name is required")
        if not patient_last:
            errors.append("Patient last name is required")
        if not patient_dob:
            errors.append("Patient date of birth is required")
        if not insurance_id:
            errors.append("Insurance ID is required")
        if not provider_first:
            errors.append("Provider first name is required")
        if not provider_last:
            errors.append("Provider last name is required")
        if not provider_npi or len(provider_npi) != 10:
            errors.append("Provider NPI must be 10 digits")
        if not service_date:
            errors.append("Service date is required")
        if not diagnoses:
            errors.append("At least one diagnosis is required")
        if not procedures:
            errors.append("At least one procedure is required")
        
        if errors:
            st.error("**Please fix the following errors:**\n" + "\n".join(f"- {e}" for e in errors))
            return None
        
        return {
            'patient_first_name': patient_first,
            'patient_last_name': patient_last,
            'patient_dob': patient_dob,
            'patient_gender': patient_gender if patient_gender != "Not specified" else None,
            'insurance_id': insurance_id,
            'group_number': group_number or None,
            'patient_phone': patient_phone or None,
            'patient_email': patient_email or None,
            'provider_first_name': provider_first,
            'provider_last_name': provider_last,
            'provider_npi': provider_npi,
            'provider_specialty': provider_specialty if provider_specialty != "Other" else None,
            'provider_phone': provider_phone or None,
            'service_date': service_date,
            'place_of_service': place_of_service.split(' - ')[0],
            'diagnoses': diagnoses,
            'procedures': procedures,
        }
    
    return None
