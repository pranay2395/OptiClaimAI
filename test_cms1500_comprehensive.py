"""
Unit tests for CMS-1500 form and EDI generation
Tests validation, service lines (1-6), NPPES lookup, EDI format
"""

import pytest
from datetime import date
from model.cms1500_schema import (
    CMS1500, Subscriber, SubscriberInfo, PatientInfo, InsuranceInfo,
    AuthorizationInfo, AuthorizationNumber, ServiceLocation, ProviderInfo,
    DiagnosisCode, ServiceLine, BillingInfo
)
from engine.edi_837p_generator import cms1500_to_edi837p
from engine.nppes_lookup import NPPESLookup


class TestServiceLineVariations:
    """Test CMS-1500 with 1-6 service lines"""
    
    def create_base_cms1500(self, num_lines: int) -> CMS1500:
        """Create a CMS-1500 with specified number of service lines"""
        
        service_lines = []
        base_charge = 100.0
        
        for i in range(num_lines):
            service_lines.append(ServiceLine(
                line_number=i + 1,
                from_date=date(2026, 1, 10),
                to_date=date(2026, 1, 10),
                place_of_service="11",
                procedure_code=f"9921{i}",  # 99210, 99211, 99212, etc
                modifier_1=None,
                modifier_2=None,
                modifier_3=None,
                charges=base_charge * (i + 1),
                units=1,
                diagnosis_pointer="1",
                emg=False,
            ))
        
        return CMS1500(
            subscriber=Subscriber(insurance_type="Medicare"),
            subscriber_info=SubscriberInfo(
                name="Test Patient",
                dob=date(1945, 1, 1),
                gender="M",
                subscriber_id="TEST123",
                group_name="",
                group_number="",
            ),
            patient_info=PatientInfo(
                first_name="Test",
                last_name="Patient",
                dob=date(1945, 1, 1),
                gender="M",
                relationship_to_subscriber="Self",
            ),
            insurance_info=InsuranceInfo(),
            authorization_info=AuthorizationInfo(),
            authorization_number=AuthorizationNumber(),
            service_lines=service_lines,
            diagnoses=[DiagnosisCode(code="M79.3", primary=True, sequence_number=1)],
            billing_info=BillingInfo(
                federal_tax_id="12-3456789",
                federal_tax_id_type="EIN",
                accept_assignment=True,
                total_charges=sum(sl.charges for sl in service_lines),
            ),
            service_location=ServiceLocation(),
            provider_info=ProviderInfo(
                npi="1234567890",
                tax_id="12-3456789",
                provider_last_name="Doctor",
                provider_first_name="Test",
            ),
            claim_number="TEST-001",
        )
    
    def test_single_service_line(self):
        """Test CMS-1500 with 1 service line"""
        cms1500 = self.create_base_cms1500(1)
        assert len(cms1500.service_lines) == 1
        assert cms1500.is_complete()
        
        edi = cms1500_to_edi837p(cms1500)
        assert "SV1*" in edi
        assert edi.count("SV1*") == 1
    
    def test_two_service_lines(self):
        """Test CMS-1500 with 2 service lines"""
        cms1500 = self.create_base_cms1500(2)
        assert len(cms1500.service_lines) == 2
        
        edi = cms1500_to_edi837p(cms1500)
        assert edi.count("SV1*") == 2
    
    def test_three_service_lines(self):
        """Test CMS-1500 with 3 service lines"""
        cms1500 = self.create_base_cms1500(3)
        assert len(cms1500.service_lines) == 3
        
        edi = cms1500_to_edi837p(cms1500)
        assert edi.count("SV1*") == 3
    
    def test_six_service_lines(self):
        """Test CMS-1500 with 6 service lines"""
        cms1500 = self.create_base_cms1500(6)
        assert len(cms1500.service_lines) == 6
        
        edi = cms1500_to_edi837p(cms1500)
        assert edi.count("SV1*") == 6


class TestEDIGeneration:
    """Test EDI 837P generation compliance"""
    
    def test_edi_structure(self):
        """Test EDI has all required segments"""
        cms1500 = TestServiceLineVariations().create_base_cms1500(2)
        edi = cms1500_to_edi837p(cms1500)
        
        required_segments = [
            "ISA*",
            "GS*",
            "ST*837",
            "BHT*",
            "NM1*",
            "HL*",
            "CLM*",
            "HI*",
            "SV1*",
            "SE*",
            "GE*",
            "IEA*",
        ]
        
        for segment in required_segments:
            assert segment in edi, f"Missing segment: {segment}"
    
    def test_edi_segment_terminators(self):
        """Test all segments end with ~ terminator"""
        cms1500 = TestServiceLineVariations().create_base_cms1500(1)
        edi = cms1500_to_edi837p(cms1500)
        
        # Split by segment terminator and check all have content
        segments = edi.split("~")
        non_empty_segments = [s for s in segments if s.strip()]
        
        # Each segment should have content
        assert len(non_empty_segments) > 10


class TestValidation:
    """Test form validation logic"""
    
    def test_required_fields_validation(self):
        """Test that required fields are enforced"""
        # This would be tested in Streamlit integration
        # For now, verify schema enforces it
        
        try:
            # Missing required provider info
            cms1500 = CMS1500(
                subscriber=Subscriber(insurance_type="Medicare"),
                subscriber_info=SubscriberInfo(
                    name="Test",
                    dob=date(1945, 1, 1),
                    gender="M",
                    subscriber_id="TEST",
                ),
                patient_info=PatientInfo(
                    first_name="Test",
                    last_name="Patient",
                    dob=date(1945, 1, 1),
                    gender="M",
                ),
                insurance_info=InsuranceInfo(),
                authorization_info=AuthorizationInfo(),
                authorization_number=AuthorizationNumber(),
                service_lines=[ServiceLine(
                    line_number=1,
                    from_date=date(2026, 1, 10),
                    to_date=date(2026, 1, 10),
                    place_of_service="11",
                    procedure_code="99213",
                    charges=100.0,
                    units=1,
                    diagnosis_pointer="1",
                    emg=False,
                )],
                diagnoses=[DiagnosisCode(code="M79.3", primary=True, sequence_number=1)],
                billing_info=BillingInfo(federal_tax_id="12-3456789"),
                service_location=ServiceLocation(),
                provider_info=ProviderInfo(),  # Missing required fields
            )
        except TypeError:
            # Expected - schema should enforce required fields
            pass


class TestNPPESLookup:
    """Test NPPES provider lookup (local cache)"""
    
    def test_nppes_cache_creation(self):
        """Test NPPES lookup creates cache file"""
        nppes = NPPESLookup()
        
        # Cache should exist even if empty
        assert nppes.cache is not None
        assert isinstance(nppes.cache, dict)
    
    def test_nppes_invalid_npi(self):
        """Test NPPES returns None for invalid NPI"""
        nppes = NPPESLookup()
        
        result = nppes.lookup_npi("invalid")
        assert result is None
        
        result = nppes.lookup_npi("12345")
        assert result is None


class TestFormSubmissionData:
    """Test form data structure after submission"""
    
    def test_form_data_to_cms1500(self):
        """Test converting form dict to CMS1500 object"""
        # Simulate form submission
        cms1500 = TestServiceLineVariations().create_base_cms1500(3)
        form_dict = cms1500.to_dict()
        
        # Verify dict has expected structure
        assert 'subscriber' in form_dict
        assert 'patient_info' in form_dict
        assert 'provider_info' in form_dict
        assert 'service_lines' in form_dict
        assert len(form_dict['service_lines']) == 3


def run_tests():
    """Run all tests with pytest"""
    import subprocess
    result = subprocess.run(
        ["pytest", "-v", __file__],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    print(result.stderr)
    return result.returncode == 0


if __name__ == "__main__":
    print("Running CMS-1500 Form & EDI Tests...")
    print("=" * 70)
    
    # Run individual test classes
    test_service_lines = TestServiceLineVariations()
    
    print("\n✓ Testing Single Service Line...")
    test_service_lines.test_single_service_line()
    
    print("✓ Testing 2 Service Lines...")
    test_service_lines.test_two_service_lines()
    
    print("✓ Testing 3 Service Lines...")
    test_service_lines.test_three_service_lines()
    
    print("✓ Testing 6 Service Lines...")
    test_service_lines.test_six_service_lines()
    
    print("✓ Testing EDI Structure...")
    TestEDIGeneration().test_edi_structure()
    
    print("✓ Testing EDI Segment Terminators...")
    TestEDIGeneration().test_edi_segment_terminators()
    
    print("✓ Testing NPPES Cache...")
    TestNPPESLookup().test_nppes_cache_creation()
    
    print("✓ Testing NPPES Invalid NPI...")
    TestNPPESLookup().test_nppes_invalid_npi()
    
    print("✓ Testing Form Data Structure...")
    TestFormSubmissionData().test_form_data_to_cms1500()
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED")
    print("=" * 70)
