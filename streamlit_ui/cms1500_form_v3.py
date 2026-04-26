"""
Patient intake form designed for DME suppliers and small doctor offices.
"""

from __future__ import annotations

from datetime import date

import streamlit as st


def render_cms1500_form() -> dict | None:
    st.subheader("Patient intake and claim preparation")
    st.caption("Capture the office or DME intake once, then review, download, or automate the package.")

    with st.form("quick_claim_form", clear_on_submit=False):
        st.markdown("**Patient demographics**")
        col1, col2, col3 = st.columns(3)
        with col1:
            patient_first = st.text_input("Patient first name *")
            patient_phone = st.text_input("Patient phone")
        with col2:
            patient_last = st.text_input("Patient last name *")
            patient_email = st.text_input("Patient email")
        with col3:
            patient_dob = st.date_input("Date of birth *", value=date(1980, 1, 1))
            patient_gender = st.selectbox("Gender", ["", "M", "F", "Other"])

        col1, col2, col3 = st.columns(3)
        with col1:
            patient_address = st.text_input("Street address")
        with col2:
            patient_city = st.text_input("City")
        with col3:
            patient_state = st.text_input("State / province")
        patient_zip = st.text_input("ZIP / postal code")

        st.markdown("**Coverage and payer**")
        col1, col2, col3 = st.columns(3)
        with col1:
            insurance_id = st.text_input("Member / insurance ID *")
        with col2:
            payer_name = st.selectbox(
                "Payer *",
                ["Medicare", "Medicaid", "Blue Cross Blue Shield", "Aetna", "Cigna", "UnitedHealthcare", "Other"],
            )
        with col3:
            group_number = st.text_input("Group number")

        st.markdown("**Provider and order details**")
        col1, col2, col3 = st.columns(3)
        with col1:
            provider_first = st.text_input("Rendering provider first name *")
            provider_phone = st.text_input("Provider phone")
        with col2:
            provider_last = st.text_input("Rendering provider last name *")
            provider_tax_id = st.text_input("Tax ID")
        with col3:
            provider_npi = st.text_input("Rendering provider NPI *", max_chars=10)
            provider_specialty = st.text_input("Specialty")

        col1, col2 = st.columns(2)
        with col1:
            ordering_provider = st.text_input("Ordering / referring provider")
        with col2:
            ordering_provider_npi = st.text_input("Ordering provider NPI")

        st.markdown("**Visit or DME order**")
        col1, col2, col3 = st.columns(3)
        with col1:
            service_date = st.date_input("Service / order date *", value=date.today())
        with col2:
            place_of_service = st.selectbox(
                "Place of service *",
                ["11", "12", "20", "21", "22", "24", "31", "41"],
                format_func=lambda code: {
                    "11": "11 - Office",
                    "12": "12 - Home",
                    "20": "20 - Urgent care",
                    "21": "21 - Inpatient hospital",
                    "22": "22 - Outpatient hospital",
                    "24": "24 - Ambulatory surgical center",
                    "31": "31 - Skilled nursing facility",
                    "41": "41 - Ambulance (land)",
                }[code],
            )
        with col3:
            service_category = st.selectbox(
                "Service category",
                ["Office visit", "DME", "Physical therapy", "Behavioral health", "Imaging", "Home health", "Other"],
            )

        with st.expander("DME-specific intake"):
            col1, col2, col3 = st.columns(3)
            with col1:
                dme_item = st.text_input("Equipment / supply name")
            with col2:
                dme_hcpcs = st.text_input("HCPCS / product code")
            with col3:
                dme_quantity = st.number_input("Quantity", min_value=1.0, step=1.0, value=1.0)
            col1, col2, col3 = st.columns(3)
            with col1:
                dme_rental_purchase = st.selectbox("Rental / purchase", ["Not applicable", "Rental", "Purchase"])
            with col2:
                length_of_need = st.text_input("Length of need")
            with col3:
                delivery_date = st.date_input("Delivery date", value=date.today())

        with st.expander("Authorization and support docs"):
            has_prior_auth = st.checkbox("Prior authorization already obtained")
            referral_on_file = st.checkbox("Referral on file")
            chart_note_ready = st.checkbox("Clinical note ready")
            physician_order_ready = st.checkbox("Physician order ready")

        st.markdown("**Diagnosis and procedures**")
        diagnoses = []
        for index in range(4):
            col1, col2 = st.columns([1, 2])
            with col1:
                diag_code = st.text_input(f"Diagnosis {index + 1}", max_chars=8, placeholder="e.g. M54.50")
            with col2:
                diag_desc = st.text_input(f"Diagnosis {index + 1} description", placeholder="Optional description")
            if diag_code.strip():
                diagnoses.append({"code": diag_code.strip().upper(), "description": diag_desc.strip() or None})

        procedures = []
        for index in range(4):
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1.2])
            with col1:
                proc_code = st.text_input(f"Procedure {index + 1}", max_chars=6, placeholder="99213 / E1399")
            with col2:
                proc_units = st.number_input(f"Units {index + 1}", min_value=1.0, step=1.0, value=1.0)
            with col3:
                proc_charge = st.number_input(f"Charge {index + 1}", min_value=0.0, step=1.0, value=0.0)
            with col4:
                proc_desc = st.text_input(f"Description {index + 1}", placeholder="Optional")
            if proc_code.strip():
                procedures.append(
                    {
                        "code": proc_code.strip().upper(),
                        "units": proc_units,
                        "charge": proc_charge,
                        "description": proc_desc.strip() or None,
                    }
                )

        notes = st.text_area(
            "Office notes / intake notes",
            placeholder="Referral details, delivery notes, facility notes, medical necessity summary, etc.",
            height=120,
        )

        submitted = st.form_submit_button("Validate and package intake", type="primary", use_container_width=True)

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
        errors.append("Rendering provider first name is required.")
    if not provider_last.strip():
        errors.append("Rendering provider last name is required.")
    if len(provider_npi.strip()) != 10 or not provider_npi.strip().isdigit():
        errors.append("Rendering provider NPI must be exactly 10 digits.")
    if not diagnoses:
        errors.append("At least one diagnosis code is required.")
    if not procedures:
        errors.append("At least one procedure or HCPCS code is required.")
    if any(item["charge"] <= 0 for item in procedures):
        errors.append("Each billed line needs a charge greater than 0.")

    if errors:
        st.error("\n".join(f"- {error}" for error in errors))
        return None

    return {
        "patient_first_name": patient_first.strip(),
        "patient_last_name": patient_last.strip(),
        "patient_dob": patient_dob,
        "patient_gender": patient_gender or None,
        "patient_phone": patient_phone.strip() or None,
        "patient_email": patient_email.strip() or None,
        "patient_address": patient_address.strip() or None,
        "patient_city": patient_city.strip() or None,
        "patient_state": patient_state.strip() or None,
        "patient_zip": patient_zip.strip() or None,
        "insurance_id": insurance_id.strip(),
        "payer_name": payer_name,
        "group_number": group_number.strip() or None,
        "provider_first_name": provider_first.strip(),
        "provider_last_name": provider_last.strip(),
        "provider_npi": provider_npi.strip(),
        "provider_specialty": provider_specialty.strip() or None,
        "provider_phone": provider_phone.strip() or None,
        "provider_tax_id": provider_tax_id.strip() or None,
        "provider_facility": None,
        "ordering_provider": ordering_provider.strip() or None,
        "ordering_provider_npi": ordering_provider_npi.strip() or None,
        "service_date": service_date,
        "place_of_service": place_of_service,
        "service_category": service_category,
        "dme_item": dme_item.strip() or None,
        "dme_hcpcs": dme_hcpcs.strip().upper() or None,
        "dme_quantity": dme_quantity,
        "dme_rental_purchase": dme_rental_purchase,
        "length_of_need": length_of_need.strip() or None,
        "delivery_date": delivery_date,
        "has_prior_auth": has_prior_auth,
        "referral_on_file": referral_on_file,
        "chart_note_ready": chart_note_ready,
        "physician_order_ready": physician_order_ready,
        "diagnoses": diagnoses,
        "procedures": procedures,
        "notes": notes.strip() or None,
    }
