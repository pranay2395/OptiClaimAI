"""
CMS-1500 Form UI Component - Complete claim form in Streamlit
All boxes 1-33 exactly as specified by CMS
"""

import streamlit as st
from datetime import date, datetime
from model.cms1500_schema import (
    CMS1500, Subscriber, SubscriberInfo, PatientInfo, InsuranceInfo,
    AuthorizationInfo, AuthorizationNumber, ServiceLocation, ProviderInfo,
    DiagnosisCode, ServiceLine, BillingInfo
)


def render_cms1500_form() -> dict:
    """Render complete CMS-1500 form and return data or None"""
    
    st.header("📋 CMS-1500 Professional Claim Form")
    st.info("Complete all required fields marked with *. Boxes 1-33 as specified by CMS.")
    
    with st.form("cms_1500_form", clear_on_submit=False):
        
        # ===== BOX 1: INSURANCE TYPE =====
        st.subheader("Box 1: Insurance Type")
        col1, col2 = st.columns(2)
        with col1:
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
        
        # ===== BOXES 10-11: CONDITIONS =====
        st.subheader("Boxes 10-11: Conditions Applicable to Claim")
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
        
        # ===== BOX 23: AUTH/REFERRAL NUMBER =====
        st.subheader("Box 23: Prior Authorization/Referral Number")
        auth_number = st.text_input("Authorization Number (Optional)", key="auth_number")
        
        # ===== PROVIDER INFORMATION =====
        st.subheader("Provider Information (Boxes 24j-33)")
        col1, col2 = st.columns(2)
        with col1:
            provider_npi = st.text_input("Provider NPI *", key="provider_npi")
            provider_last = st.text_input("Provider Last Name *", key="provider_last")
        with col2:
            provider_tax_id = st.text_input("Provider Tax ID (EIN/SSN) *", key="provider_tax_id")
            provider_first = st.text_input("Provider First Name *", key="provider_first")
        
        col1, col2 = st.columns(2)
        with col1:
            provider_specialty = st.text_input("Specialty (Optional)", key="provider_specialty")
            provider_phone = st.text_input("Phone (Optional)", key="provider_phone")
        with col2:
            provider_middle = st.text_input("Middle Initial (Optional)", key="provider_middle")
            provider_credentials = st.text_input("Credentials (Optional)", key="provider_credentials")
        
        col1, col2 = st.columns(2)
        with col1:
            provider_address = st.text_input("Address (Optional)", key="provider_address")
            provider_city = st.text_input("City (Optional)", key="provider_city")
        with col2:
            provider_state = st.text_input("State (Optional)", key="provider_state")
            provider_zip = st.text_input("ZIP (Optional)", key="provider_zip")
        
        # ===== BOX 21: DIAGNOSES =====
        st.subheader("Box 21: Diagnosis Codes (ICD-10)")
        st.write("Add up to 4 diagnosis codes:")
        
        diagnoses = []
        for i in range(4):
            col1, col2, col3 = st.columns([3, 1, 2])
            with col1:
                diag_code = st.text_input(f"Diagnosis {i+1} Code", key=f"diag_code_{i}")
            with col2:
                is_primary = st.checkbox("Primary", key=f"diag_primary_{i}")
            with col3:
                st.write("")  # Spacer
            
            if diag_code:
                diagnoses.append(DiagnosisCode(code=diag_code, primary=is_primary, sequence_number=i+1))
        
        if not diagnoses:
            st.warning("At least one diagnosis code is required")
        
        # ===== BOX 24: SERVICE LINES =====
        st.subheader("Box 24: Service Line Details (Repeatable)")
        st.write("Add service lines for this claim:")
        
        service_lines = []
        num_lines = st.number_input("Number of Service Lines", min_value=1, max_value=10, value=1, key="num_lines")
        
        for line_num in range(int(num_lines)):
            st.write(f"**Service Line {line_num + 1}**")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                from_date = st.date_input(f"From Date *", key=f"from_date_{line_num}")
            with col2:
                to_date = st.date_input(f"To Date *", key=f"to_date_{line_num}")
            with col3:
                procedure_code = st.text_input(f"Procedure Code (CPT/HCPCS) *", key=f"proc_code_{line_num}")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                place_of_service = st.text_input(f"Place of Service *", value="11", key=f"pos_{line_num}")
            with col2:
                units = st.number_input(f"Units", min_value=1, value=1, key=f"units_{line_num}")
            with col3:
                charges = st.number_input(f"Charges ($) *", min_value=0.0, value=0.0, key=f"charges_{line_num}")
            with col4:
                st.write("")  # Spacer
            
            col1, col2, col3 = st.columns(3)
            with col1:
                modifier_1 = st.text_input(f"Modifier 1", key=f"mod1_{line_num}")
            with col2:
                modifier_2 = st.text_input(f"Modifier 2", key=f"mod2_{line_num}")
            with col3:
                modifier_3 = st.text_input(f"Modifier 3", key=f"mod3_{line_num}")
            
            diag_pointer = st.text_input(f"Diagnosis Pointer", value="1", key=f"diag_ptr_{line_num}")
            
            if procedure_code and charges > 0:
                service_lines.append(ServiceLine(
                    line_number=line_num + 1,
                    from_date=from_date,
                    to_date=to_date,
                    place_of_service=place_of_service,
                    procedure_code=procedure_code,
                    modifier_1=modifier_1 or None,
                    modifier_2=modifier_2 or None,
                    modifier_3=modifier_3 or None,
                    charges=charges,
                    units=units,
                    diagnosis_pointer=diag_pointer,
                ))
            
            st.divider()
        
        if not service_lines:
            st.warning("At least one service line with charges is required")
        
        # ===== FACILITY INFORMATION =====
        st.subheader("Boxes 32-33: Facility Information (Optional)")
        col1, col2 = st.columns(2)
        with col1:
            facility_name = st.text_input("Facility Name (Optional)", key="facility_name")
            facility_npi = st.text_input("Facility NPI (Optional)", key="facility_npi")
        with col2:
            facility_address = st.text_input("Facility Address (Optional)", key="facility_address")
            facility_city = st.text_input("Facility City (Optional)", key="facility_city")
        
        col1, col2 = st.columns(2)
        with col1:
            facility_state = st.text_input("Facility State (Optional)", key="facility_state")
        with col2:
            facility_zip = st.text_input("Facility ZIP (Optional)", key="facility_zip")
        
        # ===== BILLING INFORMATION =====
        st.subheader("Boxes 25-31: Billing Information")
        col1, col2 = st.columns(2)
        with col1:
            federal_tax_id = st.text_input("Federal Tax ID *", key="fed_tax_id")
            tax_id_type = st.selectbox("Tax ID Type", ["EIN", "SSN"], key="tax_id_type")
        with col2:
            accept_assignment = st.checkbox("Accept Assignment", value=True, key="accept_assignment")
            claim_number = st.text_input("Claim Number (Optional)", key="claim_num")
        
        # Submission button
        submitted = st.form_submit_button("🎯 Submit & Convert to EDI", type="primary")
        
        if submitted:
            # Validation
            errors = []
            if not subscriber_name:
                errors.append("Subscriber name required")
            if not patient_first or not patient_last:
                errors.append("Patient name required")
            if not provider_npi or not provider_last or not provider_first:
                errors.append("Provider information required")
            if not diagnoses:
                errors.append("At least one diagnosis required")
            if not service_lines:
                errors.append("At least one service line required")
            if not federal_tax_id:
                errors.append("Federal tax ID required")
            
            if errors:
                st.error("Please fix these errors:\n" + "\n".join(f"• {e}" for e in errors))
                return None
            
            # Build CMS-1500 object
            cms1500 = CMS1500(
                subscriber=Subscriber(insurance_type=insurance_type),
                subscriber_info=SubscriberInfo(
                    name=subscriber_name,
                    dob=subscriber_dob,
                    gender=subscriber_gender,
                    subscriber_id=subscriber_id,
                    group_name=group_name,
                    group_number=group_number,
                ),
                patient_info=PatientInfo(
                    first_name=patient_first,
                    last_name=patient_last,
                    dob=patient_dob,
                    gender=patient_gender,
                    relationship_to_subscriber=relationship,
                ),
                insurance_info=InsuranceInfo(),
                authorization_info=AuthorizationInfo(
                    employment_related=employment,
                    auto_accident=auto_accident,
                    other_accident=other_accident,
                    accident_state=accident_state,
                ),
                authorization_number=AuthorizationNumber(auth_number=auth_number),
                service_lines=service_lines,
                diagnoses=diagnoses,
                billing_info=BillingInfo(
                    federal_tax_id=federal_tax_id,
                    federal_tax_id_type=tax_id_type,
                    accept_assignment=accept_assignment,
                    total_charges=sum(sl.charges for sl in service_lines),
                ),
                service_location=ServiceLocation(
                    facility_name=facility_name,
                    facility_npi=facility_npi,
                    facility_address=facility_address,
                    facility_city=facility_city,
                    facility_state=facility_state,
                    facility_zip=facility_zip,
                ),
                provider_info=ProviderInfo(
                    npi=provider_npi,
                    tax_id=provider_tax_id,
                    provider_last_name=provider_last,
                    provider_first_name=provider_first,
                    provider_middle_initial=provider_middle,
                    provider_credentials=provider_credentials,
                    provider_specialty=provider_specialty,
                    phone=provider_phone,
                    address=provider_address,
                    city=provider_city,
                    state=provider_state,
                    zip_code=provider_zip,
                ),
                claim_number=claim_number,
            )
            
            return cms1500.to_dict()
    
    return None
