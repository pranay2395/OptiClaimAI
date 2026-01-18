"""
CMS-1500 Form UI Component - STRICTLY STREAMLIT COMPLIANT
Render phase ONLY: No validation, no API calls, no side effects
Returns dict ONLY on submit, None otherwise
"""

import streamlit as st
from datetime import date


def render_cms1500_form() -> dict:
    """
    Render CMS-1500 form with strict Streamlit compliance.
    
    RULES:
    - NO buttons inside form (only st.form_submit_button allowed)
    - NO API calls during render
    - NO validation during render
    - Returns None if not submitted
    - Returns dict ONLY when submitted
    """
    
    st.header("📋 CMS-1500 Professional Claim Form")
    st.info("Complete all required fields marked with *")
    
    with st.form("cms_1500_form", clear_on_submit=False):
        
        # ===== BOX 1: INSURANCE TYPE =====
        st.subheader("Box 1: Insurance Type")
        insurance_type = st.selectbox(
            "Insurance Type *",
            ["Medicare", "Medicaid", "TRICARE", "CHAMPUS", "Group Health", "FECA", "Other"],
            key="box1"
        )
        
        # ===== BOXES 1a-1d: SUBSCRIBER INFORMATION =====
        st.subheader("Boxes 1a-1d: Subscriber Information")
        col1, col2 = st.columns(2)
        with col1:
            subscriber_name = st.text_input("Subscriber Name *", key="sub_name")
            subscriber_dob = st.date_input("Subscriber DOB *", key="sub_dob", format="YYYY/MM/DD", min_value=date(1860, 1, 1))
        with col2:
            subscriber_gender = st.selectbox("Gender", ["M", "F"], key="sub_gender")
            subscriber_id = st.text_input("Subscriber ID *", key="sub_id")
        
        col1, col2 = st.columns(2)
        with col1:
            group_name = st.text_input("Group Name (Optional)", key="group_name")
        with col2:
            group_number = st.text_input("Group Number (Optional)", key="group_num")
        
        st.divider()
        
        # ===== BOXES 2-5: PATIENT INFORMATION =====
        st.subheader("Boxes 2-5: Patient Information")
        col1, col2 = st.columns(2)
        with col1:
            patient_first = st.text_input("Patient First Name *", key="pat_first")
            patient_dob = st.date_input("Patient DOB *", key="pat_dob", format="YYYY/MM/DD", min_value=date(1860, 1, 1))
        with col2:
            patient_last = st.text_input("Patient Last Name *", key="pat_last")
            patient_gender = st.selectbox("Patient Gender", ["M", "F"], key="pat_gender")
        
        relationship = st.selectbox(
            "Patient Relationship to Subscriber",
            ["Self", "Spouse", "Child", "Other"],
            key="relationship"
        )
        
        st.divider()
        
        # ===== BOXES 10-11: CONDITIONS =====
        st.subheader("Boxes 10-11: Conditions")
        col1, col2, col3 = st.columns(3)
        with col1:
            employment = st.checkbox("Employment Related", key="employment")
        with col2:
            auto_accident = st.checkbox("Auto Accident", key="auto_accident")
        with col3:
            other_accident = st.checkbox("Other Accident", key="other_accident")
        
        if auto_accident or other_accident:
            accident_state = st.text_input("State", key="accident_state")
        else:
            accident_state = None
        
        st.divider()
        
        # ===== BOX 23: AUTH/REFERRAL =====
        st.subheader("Box 23: Prior Authorization/Referral Number")
        auth_number = st.text_input("Authorization Number (Optional)", key="auth_number")
        
        st.divider()
        
        # ===== PROVIDER INFORMATION =====
        st.subheader("Provider Information")
        col1, col2 = st.columns(2)
        with col1:
            provider_npi = st.text_input("Provider NPI *", key="provider_npi")
            provider_tax_id = st.text_input("Provider Tax ID *", key="provider_tax_id")
        with col2:
            provider_first = st.text_input("Provider First Name *", key="provider_first")
            provider_last = st.text_input("Provider Last Name *", key="provider_last")
        
        col1, col2 = st.columns(2)
        with col1:
            provider_middle = st.text_input("Middle Initial (Optional)", key="provider_middle")
            provider_specialty = st.text_input("Specialty (Optional)", key="provider_specialty")
        with col2:
            provider_phone = st.text_input("Phone (Optional)", key="provider_phone")
            provider_credentials = st.text_input("Credentials (Optional)", key="provider_credentials")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            provider_address = st.text_input("Address (Optional)", key="provider_address")
        with col2:
            provider_city = st.text_input("City (Optional)", key="provider_city")
        with col3:
            provider_state = st.text_input("State (Optional)", key="provider_state")
        
        provider_zip = st.text_input("ZIP (Optional)", key="provider_zip")
        
        st.divider()
        
        # ===== BOX 21: DIAGNOSES =====
        st.subheader("Box 21: Diagnosis Codes (ICD-10)")
        diagnoses = []
        for i in range(4):
            col1, col2 = st.columns([3, 1])
            with col1:
                diag_code = st.text_input(f"Diagnosis {i+1} Code", key=f"diag_code_{i}")
            with col2:
                is_primary = st.checkbox("Primary", key=f"diag_primary_{i}")
            
            if diag_code:
                diagnoses.append({
                    'code': diag_code,
                    'primary': is_primary,
                    'sequence_number': i + 1
                })
        
        st.divider()
        
        # ===== BOX 24: SERVICE LINES =====
        st.subheader("Box 24: Service Line Details")
        num_lines = st.number_input("Number of Service Lines", min_value=1, max_value=10, value=1, key="num_lines")
        
        service_lines = []
        for line_num in range(int(num_lines)):
            st.write(f"**Service Line {line_num + 1}**")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                from_date = st.date_input(f"From Date *", key=f"from_date_{line_num}")
            with col2:
                to_date = st.date_input(f"To Date *", key=f"to_date_{line_num}")
            with col3:
                procedure_code = st.text_input(f"Procedure Code *", key=f"proc_code_{line_num}")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                place_of_service = st.text_input(f"Place of Service *", value="11", key=f"pos_{line_num}")
            with col2:
                units = st.number_input(f"Units", min_value=1, value=1, key=f"units_{line_num}")
            with col3:
                charges = st.number_input(f"Charges ($) *", min_value=0.0, value=0.0, key=f"charges_{line_num}")
            with col4:
                st.write("")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                modifier_1 = st.text_input(f"Modifier 1", key=f"mod1_{line_num}")
            with col2:
                modifier_2 = st.text_input(f"Modifier 2", key=f"mod2_{line_num}")
            with col3:
                modifier_3 = st.text_input(f"Modifier 3", key=f"mod3_{line_num}")
            
            diag_pointer = st.text_input(f"Diagnosis Pointer", value="1", key=f"diag_ptr_{line_num}")
            
            service_lines.append({
                'line_number': line_num + 1,
                'from_date': from_date,
                'to_date': to_date,
                'place_of_service': place_of_service,
                'procedure_code': procedure_code,
                'modifier_1': modifier_1 or None,
                'modifier_2': modifier_2 or None,
                'modifier_3': modifier_3 or None,
                'charges': charges,
                'units': units,
                'diagnosis_pointer': diag_pointer,
            })
            
            st.divider()
        
        # ===== FACILITY INFORMATION =====
        st.subheader("Boxes 32-33: Facility Information (Optional)")
        col1, col2 = st.columns(2)
        with col1:
            facility_name = st.text_input("Facility Name", key="facility_name")
            facility_npi = st.text_input("Facility NPI", key="facility_npi")
        with col2:
            facility_address = st.text_input("Facility Address", key="facility_address")
            facility_city = st.text_input("Facility City", key="facility_city")
        
        col1, col2 = st.columns(2)
        with col1:
            facility_state = st.text_input("Facility State", key="facility_state")
        with col2:
            facility_zip = st.text_input("Facility ZIP", key="facility_zip")
        
        st.divider()
        
        # ===== BILLING INFORMATION =====
        st.subheader("Boxes 25-31: Billing Information")
        col1, col2 = st.columns(2)
        with col1:
            federal_tax_id = st.text_input("Federal Tax ID *", key="fed_tax_id")
            tax_id_type = st.selectbox("Tax ID Type", ["EIN", "SSN"], key="tax_id_type")
        with col2:
            accept_assignment = st.checkbox("Accept Assignment", value=True, key="accept_assignment")
            claim_number = st.text_input("Claim Number (Optional)", key="claim_num")
        
        st.divider()
        
        # SUBMIT BUTTON - ONLY ALLOWED BUTTON INSIDE FORM
        submitted = st.form_submit_button("🎯 Submit & Convert to EDI", type="primary")
    
    # RETURN DATA ONLY IF SUBMITTED
    if submitted:
        return {
            'insurance_type': insurance_type,
            'subscriber_name': subscriber_name,
            'subscriber_dob': subscriber_dob,
            'subscriber_gender': subscriber_gender,
            'subscriber_id': subscriber_id,
            'group_name': group_name,
            'group_number': group_number,
            'patient_first': patient_first,
            'patient_last': patient_last,
            'patient_dob': patient_dob,
            'patient_gender': patient_gender,
            'relationship': relationship,
            'employment': employment,
            'auto_accident': auto_accident,
            'other_accident': other_accident,
            'accident_state': accident_state,
            'auth_number': auth_number,
            'provider_npi': provider_npi,
            'provider_tax_id': provider_tax_id,
            'provider_first': provider_first,
            'provider_last': provider_last,
            'provider_middle': provider_middle,
            'provider_specialty': provider_specialty,
            'provider_phone': provider_phone,
            'provider_credentials': provider_credentials,
            'provider_address': provider_address,
            'provider_city': provider_city,
            'provider_state': provider_state,
            'provider_zip': provider_zip,
            'diagnoses': diagnoses,
            'service_lines': service_lines,
            'facility_name': facility_name,
            'facility_npi': facility_npi,
            'facility_address': facility_address,
            'facility_city': facility_city,
            'facility_state': facility_state,
            'facility_zip': facility_zip,
            'federal_tax_id': federal_tax_id,
            'tax_id_type': tax_id_type,
            'accept_assignment': accept_assignment,
            'claim_number': claim_number,
        }
    
    return None
