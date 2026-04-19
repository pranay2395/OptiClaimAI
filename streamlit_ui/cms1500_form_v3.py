"""
Lean claim-entry form for pre-submission review.
"""

from __future__ import annotations

from datetime import date

import streamlit as st


def render_cms1500_form() -> dict | None:
    st.subheader("Quick Claim Entry")
    st.caption("Enter the essentials first. Optional fields are hidden in expanders to keep the form short.")

    with st.form("quick_claim_form", clear_on_submit=False):
        st.markdown("**Patient**")
        col1, col2 = st.columns(2)
        with col1:
            patient_first = st.text_input("Patient first name *")
            patient_dob = st.date_input("Patient date of birth *", value=date(1980, 1, 1))
        with col2:
            patient_last = st.text_input("Patient last name *")
            patient_gender = st.selectbox("Patient gender", ["", "M", "F", "Other"])

        col1, col2 = st.columns(2)
        with col1:
            insurance_id = st.text_input("Member / insurance ID *")
        with col2:
            payer_name = st.selectbox(
                "Payer *",
                ["Medicare", "Medicaid", "Blue Cross Blue Shield", "Aetna", "Cigna", "UnitedHealthcare", "Other"],
            )

        col1, col2 = st.columns(2)
        with col1:
            place_of_service = st.selectbox(
                "Place of service *",
                ["11", "20", "21", "22", "24", "31", "41"],
                format_func=lambda code: {
                    "11": "11 - Office",
                    "20": "20 - Urgent care",
                    "21": "21 - Inpatient hospital",
                    "22": "22 - Outpatient hospital",
                    "24": "24 - Ambulatory surgical center",
                    "31": "31 - Skilled nursing facility",
                    "41": "41 - Ambulance (land)",
                }[code],
            )

        with st.expander("Optional patient contact"):
            col1, col2 = st.columns(2)
            with col1:
                patient_phone = st.text_input("Patient phone")
            with col2:
                patient_email = st.text_input("Patient email")
            group_number = st.text_input("Group number")

        st.markdown("**Provider**")
        col1, col2, col3 = st.columns(3)
        with col1:
            provider_first = st.text_input("Provider first name *")
        with col2:
            provider_last = st.text_input("Provider last name *")
        with col3:
            provider_npi = st.text_input("Provider NPI *", max_chars=10)

        with st.expander("Optional provider details"):
            col1, col2 = st.columns(2)
            with col1:
                provider_specialty = st.text_input("Specialty")
                provider_phone = st.text_input("Provider phone")
            with col2:
                provider_tax_id = st.text_input("Tax ID")
                provider_facility = st.text_input("Facility name")

        with st.expander("Authorization and support docs"):
            has_prior_auth = st.checkbox("Prior authorization already obtained")
            referral_on_file = st.checkbox("Referral on file")
            chart_note_ready = st.checkbox("Clinical note ready")

        st.markdown("**Visit & coding**")
        service_date = st.date_input("Service date *", value=date.today())

        st.caption("Diagnosis codes")
        diagnoses = []
        for index in range(3):
            diag_code = st.text_input(f"Diagnosis {index + 1}", max_chars=8, placeholder="e.g. M54.50")
            if diag_code.strip():
                diagnoses.append({"code": diag_code.strip().upper(), "description": None})

        st.caption("Procedure lines")
        procedures = []
        for index in range(3):
            col1, col2, col3 = st.columns([1.2, 1, 1])
            with col1:
                proc_code = st.text_input(f"Procedure {index + 1}", max_chars=5, placeholder="e.g. 99213")
            with col2:
                proc_units = st.number_input(f"Units {index + 1}", min_value=1.0, step=1.0, value=1.0)
            with col3:
                proc_charge = st.number_input(f"Charge {index + 1}", min_value=0.0, step=1.0, value=0.0)
            if proc_code.strip():
                procedures.append(
                    {
                        "code": proc_code.strip().upper(),
                        "units": proc_units,
                        "charge": proc_charge,
                    }
                )

        submitted = st.form_submit_button("Validate claim", type="primary", use_container_width=True)

    if not submitted:
        return None

    errors = []
    if not patient_first.strip():
        errors.append("Patient first name is required.")
    if not patient_last.strip():
        errors.append("Patient last name is required.")
    if not insurance_id.strip():
        errors.append("Member / insurance ID is required.")
    if not provider_first.strip():
        errors.append("Provider first name is required.")
    if not provider_last.strip():
        errors.append("Provider last name is required.")
    if len(provider_npi.strip()) != 10 or not provider_npi.strip().isdigit():
        errors.append("Provider NPI must be exactly 10 digits.")
    if not diagnoses:
        errors.append("At least one diagnosis code is required.")
    if not procedures:
        errors.append("At least one procedure code is required.")
    if any(item["charge"] <= 0 for item in procedures):
        errors.append("Each procedure line must have a charge greater than 0.")

    if errors:
        st.error("\n".join(f"- {error}" for error in errors))
        return None

    return {
        "patient_first_name": patient_first.strip(),
        "patient_last_name": patient_last.strip(),
        "patient_dob": patient_dob,
        "patient_gender": patient_gender or None,
        "insurance_id": insurance_id.strip(),
        "payer_name": payer_name,
        "group_number": group_number.strip() or None,
        "patient_phone": patient_phone.strip() or None,
        "patient_email": patient_email.strip() or None,
        "provider_first_name": provider_first.strip(),
        "provider_last_name": provider_last.strip(),
        "provider_npi": provider_npi.strip(),
        "provider_specialty": provider_specialty.strip() or None,
        "provider_phone": provider_phone.strip() or None,
        "provider_tax_id": provider_tax_id.strip() or None,
        "provider_facility": provider_facility.strip() or None,
        "has_prior_auth": has_prior_auth,
        "referral_on_file": referral_on_file,
        "chart_note_ready": chart_note_ready,
        "service_date": service_date,
        "place_of_service": place_of_service,
        "diagnoses": diagnoses,
        "procedures": procedures,
    }
