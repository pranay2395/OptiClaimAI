"""
CMS-1500 Validation Logic
Runs ONLY after form submission
Deterministic rules mapped 1:1 to CMS-1500 boxes
"""

from typing import Dict, List, Tuple


def validate_cms1500(data: Dict) -> Tuple[bool, List[str], List[str]]:
    """
    Validate CMS-1500 form data.
    
    Args:
        data: Dict from render_cms1500_form()
    
    Returns:
        (is_valid, errors, warnings)
        - is_valid: bool - True if all required fields present
        - errors: List[str] - Hard errors (blocks submission)
        - warnings: List[str] - Soft warnings (allows submission)
    """
    
    errors = []
    warnings = []
    
    # Required fields validation
    if not data.get('subscriber_name'):
        errors.append("Subscriber name required (Box 1a)")
    
    if not data.get('patient_first') or not data.get('patient_last'):
        errors.append("Patient name (first and last) required (Boxes 2-5)")
    
    if not data.get('provider_npi'):
        errors.append("Provider NPI required (Box 24j)")
    
    if not data.get('provider_first') or not data.get('provider_last'):
        errors.append("Provider name (first and last) required (Box 24j)")
    
    if not data.get('federal_tax_id'):
        errors.append("Federal Tax ID required (Box 25)")
    
    # Diagnoses validation
    diagnoses = data.get('diagnoses', [])
    if not diagnoses:
        errors.append("At least one diagnosis code required (Box 21)")
    elif len(diagnoses) > 4:
        errors.append("Maximum 4 diagnoses allowed (Box 21)")
    
    # Service lines validation
    service_lines = data.get('service_lines', [])
    if not service_lines:
        errors.append("At least one service line required (Box 24)")
    
    for i, sl in enumerate(service_lines, 1):
        if not sl.get('procedure_code'):
            errors.append(f"Service line {i}: Procedure code required (Box 24D)")
        
        if sl.get('charges', 0) <= 0:
            errors.append(f"Service line {i}: Charges must be greater than 0 (Box 24F)")
    
    # Warnings for optional fields
    if not data.get('provider_tax_id'):
        warnings.append("Provider Tax ID recommended (Box 25a)")
    
    if not data.get('provider_phone'):
        warnings.append("Provider phone number recommended for follow-up")
    
    if not data.get('provider_address'):
        warnings.append("Provider address recommended for follow-up")
    
    return (len(errors) == 0, errors, warnings)


def build_cms1500_object(data: Dict):
    """
    Build CMS1500 dataclass object from form data.
    Call this ONLY after validation passes.
    """
    from datetime import date
    from model.cms1500_schema import (
        CMS1500, Subscriber, SubscriberInfo, PatientInfo, InsuranceInfo,
        AuthorizationInfo, AuthorizationNumber, ServiceLocation, ProviderInfo,
        DiagnosisCode, ServiceLine, BillingInfo
    )
    
    # Build diagnosis objects
    diagnoses = [
        DiagnosisCode(
            code=d['code'],
            primary=d['primary'],
            sequence_number=d['sequence_number']
        )
        for d in data.get('diagnoses', [])
    ]
    
    # Build service line objects
    service_lines = [
        ServiceLine(
            line_number=sl['line_number'],
            from_date=sl['from_date'],
            to_date=sl['to_date'],
            place_of_service=sl['place_of_service'],
            procedure_code=sl['procedure_code'],
            modifier_1=sl.get('modifier_1'),
            modifier_2=sl.get('modifier_2'),
            modifier_3=sl.get('modifier_3'),
            charges=sl['charges'],
            units=sl['units'],
            diagnosis_pointer=sl.get('diagnosis_pointer', '1'),
            emg=False,
        )
        for sl in data.get('service_lines', [])
    ]
    
    # Build CMS1500 object
    cms1500 = CMS1500(
        subscriber=Subscriber(insurance_type=data.get('insurance_type', 'Other')),
        subscriber_info=SubscriberInfo(
            name=data.get('subscriber_name', ''),
            dob=data.get('subscriber_dob', date(1945, 1, 1)),
            gender=data.get('subscriber_gender', 'M'),
            subscriber_id=data.get('subscriber_id', ''),
            group_name=data.get('group_name', ''),
            group_number=data.get('group_number', ''),
        ),
        patient_info=PatientInfo(
            first_name=data.get('patient_first', ''),
            last_name=data.get('patient_last', ''),
            dob=data.get('patient_dob', date(1945, 1, 1)),
            gender=data.get('patient_gender', 'M'),
            relationship_to_subscriber=data.get('relationship', 'Self'),
        ),
        insurance_info=InsuranceInfo(),
        authorization_info=AuthorizationInfo(
            employment_related=data.get('employment', False),
            auto_accident=data.get('auto_accident', False),
            other_accident=data.get('other_accident', False),
            accident_state=data.get('accident_state'),
        ),
        authorization_number=AuthorizationNumber(auth_number=data.get('auth_number')),
        service_lines=service_lines,
        diagnoses=diagnoses,
        billing_info=BillingInfo(
            federal_tax_id=data.get('federal_tax_id', ''),
            federal_tax_id_type=data.get('tax_id_type', 'EIN'),
            accept_assignment=data.get('accept_assignment', True),
            total_charges=sum(sl['charges'] for sl in data.get('service_lines', [])),
        ),
        service_location=ServiceLocation(
            facility_name=data.get('facility_name'),
            facility_npi=data.get('facility_npi'),
            facility_address=data.get('facility_address'),
            facility_city=data.get('facility_city'),
            facility_state=data.get('facility_state'),
            facility_zip=data.get('facility_zip'),
        ),
        provider_info=ProviderInfo(
            npi=data.get('provider_npi', ''),
            tax_id=data.get('provider_tax_id', ''),
            provider_last_name=data.get('provider_last', ''),
            provider_first_name=data.get('provider_first', ''),
            provider_middle_initial=data.get('provider_middle', ''),
            provider_credentials=data.get('provider_credentials', ''),
            provider_specialty=data.get('provider_specialty', ''),
            phone=data.get('provider_phone', ''),
            address=data.get('provider_address', ''),
            city=data.get('provider_city', ''),
            state=data.get('provider_state', ''),
            zip_code=data.get('provider_zip', ''),
        ),
        claim_number=data.get('claim_number'),
    )
    
    return cms1500
