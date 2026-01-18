"""
Complete CMS-1500 Form Test - Fills entire form and generates 837 EDI file
"""

from datetime import date
from model.cms1500_schema import (
    CMS1500, Subscriber, SubscriberInfo, PatientInfo, InsuranceInfo,
    AuthorizationInfo, AuthorizationNumber, ServiceLocation, ProviderInfo,
    DiagnosisCode, ServiceLine, BillingInfo
)
from engine.edi_837p_generator import cms1500_to_edi837p
import json

def create_complete_form():
    """Create a fully filled CMS-1500 form with all details"""
    
    # Service lines - multiple procedures
    service_lines = [
        ServiceLine(
            line_number=1,
            from_date=date(2026, 1, 10),
            to_date=date(2026, 1, 10),
            place_of_service="11",  # Office
            procedure_code="99214",  # Office visit - moderate
            modifier_1="",
            modifier_2=None,
            modifier_3=None,
            charges=125.00,
            units=1,
            diagnosis_pointer="1",
            emg=False,
        ),
        ServiceLine(
            line_number=2,
            from_date=date(2026, 1, 10),
            to_date=date(2026, 1, 10),
            place_of_service="11",
            procedure_code="70450",  # CT Head/Brain
            modifier_1="",
            modifier_2=None,
            modifier_3=None,
            charges=450.00,
            units=1,
            diagnosis_pointer="1",
            emg=False,
        ),
        ServiceLine(
            line_number=3,
            from_date=date(2026, 1, 10),
            to_date=date(2026, 1, 10),
            place_of_service="11",
            procedure_code="71030",  # Chest X-Ray - 3 views
            modifier_1="",
            modifier_2=None,
            modifier_3=None,
            charges=85.00,
            units=1,
            diagnosis_pointer="2",
            emg=False,
        ),
    ]
    
    # Diagnoses
    diagnoses = [
        DiagnosisCode(code="R51.9", primary=True, sequence_number=1),  # Headache
        DiagnosisCode(code="J45.901", primary=False, sequence_number=2),  # Asthma
    ]
    
    # Create CMS-1500 object with all fields
    cms1500 = CMS1500(
        subscriber=Subscriber(insurance_type="Medicare"),
        subscriber_info=SubscriberInfo(
            name="Robert Johnson",
            dob=date(1945, 3, 15),
            gender="M",
            subscriber_id="123456789A",
            group_name="Medicare",
            group_number="",
        ),
        patient_info=PatientInfo(
            first_name="Robert",
            last_name="Johnson",
            dob=date(1945, 3, 15),
            gender="M",
            relationship_to_subscriber="Self",
        ),
        insurance_info=InsuranceInfo(),
        authorization_info=AuthorizationInfo(
            employment_related=False,
            auto_accident=False,
            other_accident=False,
            accident_state=None,
        ),
        authorization_number=AuthorizationNumber(auth_number="AUTH123456"),
        service_lines=service_lines,
        diagnoses=diagnoses,
        billing_info=BillingInfo(
            federal_tax_id="12-3456789",
            federal_tax_id_type="EIN",
            accept_assignment=True,
            total_charges=660.00,
        ),
        service_location=ServiceLocation(
            facility_name="Metro Medical Center",
            facility_npi="1234567890",
            facility_address="456 Hospital Drive",
            facility_city="Springfield",
            facility_state="IL",
            facility_zip="62701",
        ),
        provider_info=ProviderInfo(
            npi="1987654321",
            tax_id="98-7654321",
            provider_last_name="Smith",
            provider_first_name="Patricia",
            provider_middle_initial="M",
            provider_credentials="MD",
            provider_specialty="Internal Medicine",
            phone="217-555-0100",
            address="789 Medical Plaza",
            city="Springfield",
            state="IL",
            zip_code="62702",
        ),
        claim_number="CLM-2026-001",
    )
    
    return cms1500

def main():
    print("=" * 70)
    print("COMPLETE CMS-1500 FORM TEST WITH EDI 837P GENERATION")
    print("=" * 70)
    print()
    
    # Create fully filled form
    cms1500 = create_complete_form()
    
    # Display form summary
    print("📋 CMS-1500 FORM SUMMARY")
    print("-" * 70)
    print(f"Insurance Type:     {cms1500.subscriber.insurance_type}")
    print(f"Subscriber:         {cms1500.subscriber_info.name}")
    print(f"Subscriber DOB:     {cms1500.subscriber_info.dob}")
    print(f"Subscriber ID:      {cms1500.subscriber_info.subscriber_id}")
    print()
    print(f"Patient:            {cms1500.patient_info.first_name} {cms1500.patient_info.last_name}")
    print(f"Patient DOB:        {cms1500.patient_info.dob}")
    print(f"Relationship:       {cms1500.patient_info.relationship_to_subscriber}")
    print()
    print(f"Provider:           {cms1500.provider_info.provider_first_name} {cms1500.provider_info.provider_last_name}")
    print(f"Provider NPI:       {cms1500.provider_info.npi}")
    print(f"Specialty:          {cms1500.provider_info.provider_specialty}")
    print()
    print(f"Facility:           {cms1500.service_location.facility_name}")
    print(f"Claim Number:       {cms1500.claim_number}")
    print()
    print(f"Service Lines:      {len(cms1500.service_lines)}")
    for sl in cms1500.service_lines:
        print(f"  • {sl.procedure_code} (CPT) - ${sl.charges:.2f}")
    print()
    print(f"Diagnoses:          {len(cms1500.diagnoses)}")
    for diag in cms1500.diagnoses:
        primary_marker = " (PRIMARY)" if diag.primary else ""
        print(f"  • {diag.code}{primary_marker}")
    print()
    print(f"Total Charges:      ${cms1500.billing_info.total_charges:.2f}")
    print(f"Form Complete:      {'✅ YES' if cms1500.is_complete() else '❌ NO'}")
    print()
    
    # Generate EDI 837P
    print("=" * 70)
    print("🔄 GENERATING X12 837P EDI...")
    print("=" * 70)
    print()
    
    edi_output = cms1500_to_edi837p(cms1500)
    
    print(f"✅ EDI Generated ({len(edi_output)} characters)")
    print()
    
    # Display EDI output
    print("📄 X12 837P EDI OUTPUT")
    print("-" * 70)
    # Pretty print EDI with segments separated
    segments = edi_output.replace('~', '~\n').split('\n')
    for segment in segments[:15]:  # Show first 15 segments
        if segment:
            print(segment)
    if len(segments) > 15:
        print(f"... ({len(segments) - 15} more segments)")
    print()
    
    # Save EDI file
    edi_filename = "sample_claim_837p.837"
    with open(edi_filename, 'w') as f:
        f.write(edi_output)
    
    print(f"✅ EDI File Saved: {edi_filename}")
    print()
    
    # Save JSON representation
    json_filename = "sample_claim_cms1500.json"
    with open(json_filename, 'w') as f:
        json.dump(cms1500.to_dict(), f, indent=2, default=str)
    
    print(f"✅ JSON File Saved: {json_filename}")
    print()
    
    # Validation
    print("=" * 70)
    print("✅ EDI VALIDATION")
    print("=" * 70)
    
    validations = [
        ("ISA header", "ISA*" in edi_output),
        ("GS segment", "GS*HC" in edi_output),
        ("ST segment (837)", "ST*837" in edi_output),
        ("BHT segment", "BHT*0019" in edi_output),
        ("NM1 segments", edi_output.count("NM1*") >= 5),
        ("HL segments", edi_output.count("HL*") >= 3),
        ("CLM segment", "CLM*" in edi_output),
        ("HI segment (diagnoses)", "HI*BK" in edi_output),
        ("SV1 segments (services)", edi_output.count("SV1*") >= 3),
        ("SE segment", "SE*" in edi_output),
        ("GE segment", "GE*" in edi_output),
        ("IEA segment", "IEA*" in edi_output),
    ]
    
    for check_name, result in validations:
        status = "✓" if result else "✗"
        print(f"{status} {check_name}")
    
    all_passed = all(result for _, result in validations)
    print()
    if all_passed:
        print("✅ ALL VALIDATIONS PASSED")
    else:
        print("❌ SOME VALIDATIONS FAILED")
    
    print()
    print("=" * 70)
    print("📊 FILES GENERATED:")
    print(f"  • {edi_filename} - X12 837P EDI format (ready for submission)")
    print(f"  • {json_filename} - CMS-1500 form data in JSON")
    print("=" * 70)

if __name__ == "__main__":
    main()
