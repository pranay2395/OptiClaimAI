"""
Integration Tests for OptiClaimAI
Comprehensive testing of all modules and workflows
"""

import pytest
from datetime import date
from model.canonical_claim import CanonicalClaim, Patient, Provider, ServiceLine, Diagnosis, Payer, ClaimMetadata
from services.validation_engine import ValidationEngine, ValidationSeverity
from services.ai_engine import AIEngine
from services.npi_lookup import NPILookupService, get_npi_service
from services.edi_bridge import EDIBridgeService, get_edi_service


class TestCanonicalClaimModel:
    """Test canonical claim model"""
    
    def test_create_valid_claim(self):
        """Test creating a valid canonical claim"""
        claim = CanonicalClaim(
            patient=Patient(
                first_name="John",
                last_name="Doe",
                date_of_birth=date(1980, 1, 15),
                gender="M"
            ),
            provider=Provider(
                npi="1234567890",
                first_name="Jane",
                last_name="Smith"
            ),
            service_lines=[ServiceLine(
                service_date=date(2024, 1, 10),
                procedure_code="99213",
                line_charge=150.00
            )],
            diagnoses=[Diagnosis(
                icd10_code="J45.901",
                is_primary=True
            )]
        )
        
        assert claim.patient.first_name == "John"
        assert claim.provider.npi == "1234567890"
        assert len(claim.service_lines) == 1
        assert len(claim.diagnoses) == 1
    
    def test_claim_to_dict(self):
        """Test claim serialization to dict"""
        claim = CanonicalClaim(
            patient=Patient(
                first_name="John",
                last_name="Doe",
                date_of_birth=date(1980, 1, 15)
            ),
            provider=Provider(npi="1234567890"),
            service_lines=[ServiceLine(
                service_date=date(2024, 1, 10),
                procedure_code="99213",
                line_charge=150.00
            )],
            diagnoses=[Diagnosis(icd10_code="J45.901")]
        )
        
        claim_dict = claim.to_dict()
        assert claim_dict["patient"]["first_name"] == "John"
        assert claim_dict["provider"]["npi"] == "1234567890"
    
    def test_claim_to_json(self):
        """Test claim serialization to JSON"""
        claim = CanonicalClaim(
            patient=Patient(
                first_name="John",
                last_name="Doe",
                date_of_birth=date(1980, 1, 15)
            ),
            provider=Provider(npi="1234567890"),
            service_lines=[ServiceLine(
                service_date=date(2024, 1, 10),
                procedure_code="99213",
                line_charge=150.00
            )],
            diagnoses=[Diagnosis(icd10_code="J45.901")]
        )
        
        json_str = claim.to_json_str()
        assert "John" in json_str
        assert "1234567890" in json_str


class TestValidationEngine:
    """Test validation engine"""
    
    def test_validate_valid_claim(self):
        """Test validation of a valid claim"""
        claim_dict = {
            'patient': {
                'first_name': 'John',
                'last_name': 'Doe',
                'date_of_birth': '1980-01-15',
                'gender': 'M',
                'member_id': 'MEM123456'
            },
            'provider': {
                'npi': '1234567890',
                'first_name': 'Jane',
                'last_name': 'Smith'
            },
            'service_lines': [{
                'service_date': '2024-01-10',
                'procedure_code': '99213',
                'line_charge': 150.00
            }],
            'diagnoses': [{
                'icd10_code': 'J45.901',
                'is_primary': True
            }]
        }
        
        engine = ValidationEngine()
        result = engine.validate_claim(claim_dict)
        
        assert result.denial_risk_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert isinstance(result.denial_risk_score, float)
        assert 0 <= result.denial_risk_score <= 100
    
    def test_validate_missing_patient_name(self):
        """Test validation catches missing patient first name"""
        claim_dict = {
            'patient': {
                'last_name': 'Doe',
                'date_of_birth': '1980-01-15'
            },
            'provider': {'npi': '1234567890'},
            'service_lines': [{
                'service_date': '2024-01-10',
                'procedure_code': '99213',
                'line_charge': 150.00
            }],
            'diagnoses': [{'icd10_code': 'J45.901'}]
        }
        
        engine = ValidationEngine()
        result = engine.validate_claim(claim_dict)
        
        high_issues = [i for i in result.issues if i.severity == ValidationSeverity.HIGH]
        assert len(high_issues) > 0
    
    def test_validate_invalid_npi(self):
        """Test validation catches invalid NPI"""
        claim_dict = {
            'patient': {
                'first_name': 'John',
                'last_name': 'Doe',
                'date_of_birth': '1980-01-15'
            },
            'provider': {'npi': 'ABCD'},
            'service_lines': [{
                'service_date': '2024-01-10',
                'procedure_code': '99213',
                'line_charge': 150.00
            }],
            'diagnoses': [{'icd10_code': 'J45.901'}]
        }
        
        engine = ValidationEngine()
        result = engine.validate_claim(claim_dict)
        
        high_issues = [i for i in result.issues if i.severity == ValidationSeverity.HIGH]
        assert any("NPI" in i.issue for i in high_issues)
    
    def test_denial_risk_calculation(self):
        """Test denial risk score calculation"""
        claim_dict = {
            'patient': {
                'first_name': 'John',
                'last_name': 'Doe',
                'date_of_birth': '1980-01-15'
            },
            'provider': {'npi': '1234567890'},
            'service_lines': [{
                'service_date': '2024-01-10',
                'procedure_code': '99213',
                'line_charge': 150.00
            }],
            'diagnoses': [{'icd10_code': 'J45.901'}]
        }
        
        engine = ValidationEngine()
        result = engine.validate_claim(claim_dict)
        
        # Score should be positive (0-100)
        assert result.denial_risk_score >= 0
        assert result.denial_risk_score <= 100


class TestAIEngine:
    """Test AI engine"""
    
    def test_ai_availability_checks(self):
        """Test AI provider availability checks"""
        engine = AIEngine()
        
        # At least one provider availability check should work
        ollama = engine.is_available("ollama")
        openai = engine.is_available("openai")
        anthropic = engine.is_available("anthropic")
        
        # Should be boolean
        assert isinstance(ollama, bool)
        assert isinstance(openai, bool)
        assert isinstance(anthropic, bool)
    
    def test_basic_explanation_generation(self):
        """Test basic explanation without AI"""
        engine = AIEngine()
        
        issues = [
            {'issue': 'Missing provider first name', 'severity': 'LOW', 'fix_hint': 'Enter provider first name'}
        ]
        
        explanation = engine._basic_explanation(issues)
        
        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "Missing provider" in explanation
    
    def test_basic_suggestions_generation(self):
        """Test basic suggestions without AI"""
        engine = AIEngine()
        
        issues = [
            {'issue': 'Missing provider first name', 'severity': 'LOW', 'fix_hint': 'Enter provider first name'},
            {'issue': 'Invalid NPI format', 'severity': 'HIGH', 'fix_hint': 'Use 10-digit NPI'}
        ]
        
        suggestions = engine._basic_suggestions(issues)
        
        assert isinstance(suggestions, str)
        assert len(suggestions) > 0


class TestNPILookupService:
    """Test NPI lookup service"""
    
    def test_npi_format_validation(self):
        """Test NPI format validation"""
        service = NPILookupService()
        
        # Valid format
        assert service._is_valid_npi_format("1234567890") == True
        assert service._is_valid_npi_format("0123456789") == True
        
        # Invalid format
        assert service._is_valid_npi_format("123456789") == False  # Too short
        assert service._is_valid_npi_format("12345678901") == False  # Too long
        assert service._is_valid_npi_format("ABCD567890") == False  # Non-numeric
    
    def test_singleton_pattern(self):
        """Test NPI service singleton pattern"""
        service1 = get_npi_service()
        service2 = get_npi_service()
        
        assert service1 is service2


class TestEDIBridgeService:
    """Test EDI bridge service"""
    
    def test_edi_availability_check(self):
        """Test EDI service availability check"""
        service = EDIBridgeService()
        
        # May or may not be available depending on environment
        available = service.is_available()
        assert isinstance(available, bool)
    
    def test_basic_837p_generation(self):
        """Test basic 837P generation"""
        service = EDIBridgeService()
        
        claim_dict = {
            'patient': {
                'first_name': 'John',
                'last_name': 'Doe',
                'member_id': 'MEM123456'
            },
            'provider': {
                'npi': '1234567890',
                'first_name': 'Jane',
                'last_name': 'Smith'
            },
            'service_lines': [{
                'service_date': '2024-01-10',
                'procedure_code': '99213',
                'line_charge': 150.00
            }],
            'diagnoses': [{'icd10_code': 'J45.901'}],
            'payer': {'payer_name': 'BlueCross'}
        }
        
        edi_text, error = service.generate_edi_837p(claim_dict)
        
        if not service.is_available():
            # Basic generation should at least return something
            assert edi_text is not None or error is not None
    
    def test_edi_validation(self):
        """Test EDI validation"""
        service = EDIBridgeService()
        
        # Basic EDI structure
        edi_text = "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *200101*1200*^*00501*000000001*0*T*:"
        
        result = service.validate_edi_837p(edi_text)
        
        assert "is_valid" in result
        assert "errors" in result
        assert "warnings" in result
        assert isinstance(result["is_valid"], bool)
    
    def test_singleton_pattern(self):
        """Test EDI service singleton pattern"""
        service1 = get_edi_service()
        service2 = get_edi_service()
        
        assert service1 is service2


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows"""
    
    def test_claim_creation_to_validation(self):
        """Test creating and validating a claim"""
        # Create claim
        claim = CanonicalClaim(
            patient=Patient(
                first_name="John",
                last_name="Doe",
                date_of_birth=date(1980, 1, 15),
                gender="M"
            ),
            provider=Provider(
                npi="1234567890",
                first_name="Jane",
                last_name="Smith"
            ),
            service_lines=[ServiceLine(
                service_date=date(2024, 1, 10),
                procedure_code="99213",
                line_charge=150.00
            )],
            diagnoses=[Diagnosis(
                icd10_code="J45.901",
                is_primary=True
            )]
        )
        
        # Convert to dict
        claim_dict = claim.to_dict()
        
        # Validate
        engine = ValidationEngine()
        result = engine.validate_claim(claim_dict)
        
        # Check results
        assert result.denial_risk_score >= 0
        assert result.denial_risk_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    
    def test_claim_validation_with_ai_explanation(self):
        """Test claim validation with AI explanation"""
        claim_dict = {
            'patient': {
                'first_name': 'John',
                'last_name': 'Doe',
                'date_of_birth': '1980-01-15'
            },
            'provider': {'npi': '1234567890'},
            'service_lines': [{
                'service_date': '2024-01-10',
                'procedure_code': '99213',
                'line_charge': 150.00
            }],
            'diagnoses': [{'icd10_code': 'J45.901'}]
        }
        
        # Validate
        validation_engine = ValidationEngine()
        result = validation_engine.validate_claim(claim_dict)
        
        # Get AI explanation (will use fallback if no AI available)
        ai_engine = AIEngine()
        explanation = ai_engine.explain_issues(
            [i.to_dict() for i in result.issues],
            claim_dict
        )
        
        # Should have some explanation
        assert explanation is not None
        assert len(explanation) > 0


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
