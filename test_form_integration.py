"""
Test PDF Auto-Fill Integration with Canonical Claim
Verifies form submission and claim creation
"""

from model.canonical_claim import Patient, Provider, ServiceLine, Diagnosis, CanonicalClaim, ClaimMetadata
from datetime import date
from services.validation_engine import ValidationEngine

def test_form_submission():
    """Simulate form submission with auto-filled data"""
    
    print("=" * 60)
    print("TEST: Form Submission with Auto-Filled Data")
    print("=" * 60)
    
    # Simulate data extracted from PDF
    pdf_data = {
        "patient_first": "John",
        "patient_last": "Doe",
        "patient_dob": "1980-01-15",
        "patient_member_id": "MEM123456",
        "provider_npi": "1234567890",
        "provider_first": "Jane",
        "provider_last": "Smith",
        "service_date": "2024-12-15",
        "procedure_code": "99213",
        "charge": "150.00",
        "diagnosis_code": "J45.901"
    }
    
    print("\n📋 Extracted PDF Data:")
    for key, value in pdf_data.items():
        if value:
            print(f"  {key}: {value}")
    
    # Create claim from form data
    try:
        claim = CanonicalClaim(
            patient=Patient(
                first_name=pdf_data["patient_first"],
                last_name=pdf_data["patient_last"],
                date_of_birth=date.fromisoformat(pdf_data["patient_dob"]),
                gender="M",
                member_id=pdf_data["patient_member_id"]
            ),
            provider=Provider(
                npi=pdf_data["provider_npi"],
                first_name=pdf_data["provider_first"],
                last_name=pdf_data["provider_last"]
            ),
            service_lines=[ServiceLine(
                service_date=date.fromisoformat(pdf_data["service_date"]),
                procedure_code=pdf_data["procedure_code"],
                line_charge=float(pdf_data["charge"]),
                place_of_service_code="11"
            )],
            diagnoses=[Diagnosis(
                icd10_code=pdf_data["diagnosis_code"],
                is_primary=True
            )],
            metadata=ClaimMetadata(source="saas_portal", submission_date=date.today())
        )
        
        print("\n✅ Canonical Claim Created Successfully!")
        print(f"   Patient: {claim.patient.first_name} {claim.patient.last_name}")
        print(f"   Provider NPI: {claim.provider.npi}")
        print(f"   Service Date: {claim.service_lines[0].service_date}")
        print(f"   Procedure Code: {claim.service_lines[0].procedure_code}")
        print(f"   Line Charge: ${claim.service_lines[0].line_charge:.2f}")
        
        # Validate the claim
        print("\n🔍 Validating Claim...")
        engine = ValidationEngine()
        result = engine.validate_claim(claim.to_dict())
        
        print(f"\n✅ Validation Complete:")
        print(f"   Valid: {result.is_valid}")
        print(f"   Issues: {len(result.issues)}")
        print(f"   Denial Risk: {result.denial_risk_level}")
        
        if result.issues:
            print(f"\n   Issues Found:")
            for issue in result.issues[:3]:
                print(f"     - {issue.issue} ({issue.severity.value})")
        else:
            print(f"\n   ✅ No issues found - claim is valid!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False

def test_manual_entry():
    """Simulate manual form entry without PDF"""
    
    print("\n" + "=" * 60)
    print("TEST: Manual Form Entry (No PDF)")
    print("=" * 60)
    
    try:
        claim = CanonicalClaim(
            patient=Patient(
                first_name="Jane",
                last_name="Smith",
                date_of_birth=date(1990, 5, 20),
                gender="F",
                member_id="INS987654"
            ),
            provider=Provider(
                npi="9876543210",
                first_name="Robert",
                last_name="Johnson"
            ),
            service_lines=[ServiceLine(
                service_date=date(2024, 12, 10),
                procedure_code="99214",
                line_charge=250.00,
                place_of_service_code="12"
            )],
            diagnoses=[Diagnosis(
                icd10_code="E11.9",
                is_primary=True
            )],
            metadata=ClaimMetadata(source="saas_portal", submission_date=date.today())
        )
        
        print("\n✅ Manually Entered Claim Created!")
        print(f"   Patient: {claim.patient.first_name} {claim.patient.last_name}")
        print(f"   Procedure: {claim.service_lines[0].procedure_code}")
        print(f"   Charge: ${claim.service_lines[0].line_charge:.2f}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    result1 = test_form_submission()
    result2 = test_manual_entry()
    
    print("\n" + "=" * 60)
    if result1 and result2:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)
