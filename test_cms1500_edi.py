"""
Test CMS-1500 to X12 837P conversion
"""

from datetime import date
from model.cms1500_schema import (
    CMS1500, Subscriber, SubscriberInfo, PatientInfo, InsuranceInfo,
    AuthorizationInfo, AuthorizationNumber, ServiceLocation, ProviderInfo,
    DiagnosisCode, ServiceLine, BillingInfo
)
from engine.edi_837p_generator import cms1500_to_edi837p


def test_cms1500_to_edi837p():
    """Test converting CMS-1500 to X12 837P"""
    
    print("=" * 60)
    print("CMS-1500 to X12 837P EDI Conversion Test")
    print("=" * 60)
    
    # Create sample CMS-1500
    cms1500 = CMS1500(
        subscriber=Subscriber(insurance_type="Medicare"),
        subscriber_info=SubscriberInfo(
            name="John Smith",
            dob=date(1950, 5, 15),
            gender="M",
            subscriber_id="123456789",
            group_name="Medicare",
            group_number="",
        ),
        patient_info=PatientInfo(
            first_name="John",
            last_name="Smith",
            dob=date(1950, 5, 15),
            gender="M",
            relationship_to_subscriber="Self",
        ),
        insurance_info=InsuranceInfo(),
        authorization_info=AuthorizationInfo(
            employment_related=False,
            auto_accident=False,
            other_accident=False,
        ),
        authorization_number=AuthorizationNumber(auth_number=None),
        service_lines=[
            ServiceLine(
                line_number=1,
                from_date=date(2024, 1, 10),
                to_date=date(2024, 1, 10),
                place_of_service="11",  # Office
                emg=False,
                procedure_code="99213",  # Office visit
                modifier_1=None,
                charges=150.00,
                units=1,
                diagnosis_pointer="1",
            ),
            ServiceLine(
                line_number=2,
                from_date=date(2024, 1, 10),
                to_date=date(2024, 1, 10),
                place_of_service="11",
                emg=False,
                procedure_code="71210",  # X-ray chest
                modifier_1=None,
                charges=100.00,
                units=1,
                diagnosis_pointer="1",
            ),
        ],
        diagnoses=[
            DiagnosisCode(code="M54.5", primary=True, sequence_number=1),
        ],
        billing_info=BillingInfo(
            federal_tax_id="123456789",
            federal_tax_id_type="EIN",
            accept_assignment=True,
            total_charges=250.00,
        ),
        service_location=ServiceLocation(
            facility_name="Main Clinic",
            facility_npi="1234567890",
        ),
        provider_info=ProviderInfo(
            npi="1122334455",
            tax_id="123456789",
            provider_last_name="Johnson",
            provider_first_name="Michael",
            provider_middle_initial="R",
            provider_specialty="Internal Medicine",
            phone="555-1234",
            address="123 Main St",
            city="Anytown",
            state="CA",
            zip_code="12345",
        ),
        claim_number="CLM001",
    )
    
    print("\n✅ CMS-1500 Object Created")
    print(cms1500.summary())
    
    # Validate CMS-1500
    print("\n✓ CMS-1500 Is Complete:", cms1500.is_complete())
    
    # Convert to EDI
    print("\n📄 Generating X12 837P EDI...")
    edi_output = cms1500_to_edi837p(cms1500)
    
    print(f"\n✓ EDI Generated ({len(edi_output)} characters)")
    
    # Display EDI
    print("\n" + "=" * 60)
    print("X12 837P EDI OUTPUT")
    print("=" * 60)
    print(edi_output)
    
    # Verify EDI structure
    print("\n" + "=" * 60)
    print("EDI VALIDATION")
    print("=" * 60)
    
    checks = [
        ("ISA header present", "000000001*0*P" in edi_output),  # Check for ISA content instead of segment identifier
        ("GS segment present", "GS*" in edi_output),
        ("ST segment present", "ST*837" in edi_output),
        ("BHT segment present", "BHT*" in edi_output),
        ("NM1 segments present", edi_output.count("NM1*") >= 5),
        ("HL segments present", edi_output.count("HL*") >= 3),
        ("CLM segment present", "CLM*" in edi_output),
        ("HI segment present", "HI*" in edi_output),
        ("SV1 segments present (2 lines)", edi_output.count("SV1*") >= 2),
        ("SE segment present", "SE*" in edi_output),
        ("GE segment present", "GE*" in edi_output),
        ("IEA segment present", "IEA*" in edi_output),
    ]
    
    for check_name, check_result in checks:
        status = "✓" if check_result else "✗"
        print(f"{status} {check_name}")
    
    all_passed = all(result for _, result in checks)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = test_cms1500_to_edi837p()
    exit(0 if success else 1)
