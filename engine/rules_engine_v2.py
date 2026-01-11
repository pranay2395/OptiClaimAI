"""
Enhanced Claims Rules Engine with Severity Classification
Wraps existing rules engine and adds new validation layer
"""

from enum import Enum
from typing import List, Dict
from model.claim_schema import Claim
from engine.logger import setup_logger
import re

logger = setup_logger(__name__)


class Severity(Enum):
    """Issue severity levels"""
    CRITICAL = "🔴 CRITICAL"
    HIGH = "🟠 HIGH"
    MEDIUM = "🟡 MEDIUM"
    LOW = "🟢 LOW"
    INFO = "ℹ️ INFO"


class ValidationIssue:
    """A single validation issue with severity"""
    
    def __init__(self, severity: Severity, code: str, message: str, field: str = None):
        self.severity = severity
        self.code = code
        self.message = message  # Plain English, not EDI jargon
        self.field = field
    
    def to_dict(self):
        return {
            'severity': self.severity.value,
            'code': self.code,
            'message': self.message,
            'field': self.field
        }


class ClaimRulesEngine:
    """Deterministic validation rules for claims"""
    
    def validate(self, claim: Claim) -> Dict:
        """Run all validation rules, return issues + denial risk"""
        issues = []
        
        # Required field checks
        if not claim.patient.first_name or not claim.patient.last_name:
            issues.append(ValidationIssue(
                Severity.CRITICAL,
                'PATIENT_NAME_MISSING',
                'Patient first and last name are required.',
                'patient'
            ))
        
        if not claim.patient.date_of_birth:
            issues.append(ValidationIssue(
                Severity.CRITICAL,
                'PATIENT_DOB_MISSING',
                'Patient date of birth is required for claim submission.',
                'patient'
            ))
        
        if not claim.patient.insurance_id:
            issues.append(ValidationIssue(
                Severity.CRITICAL,
                'INSURANCE_ID_MISSING',
                'Insurance/Member ID is required.',
                'patient'
            ))
        
        if not claim.provider.first_name or not claim.provider.last_name:
            issues.append(ValidationIssue(
                Severity.CRITICAL,
                'PROVIDER_NAME_MISSING',
                'Provider first and last name are required.',
                'provider'
            ))
        
        if not claim.provider.npi:
            issues.append(ValidationIssue(
                Severity.CRITICAL,
                'PROVIDER_NPI_MISSING',
                'Provider NPI is required.',
                'provider'
            ))
        
        if claim.provider.npi and len(claim.provider.npi) != 10:
            issues.append(ValidationIssue(
                Severity.CRITICAL,
                'PROVIDER_NPI_INVALID',
                f'Provider NPI must be exactly 10 digits (provided: {claim.provider.npi}).',
                'provider'
            ))
        
        if not claim.diagnoses:
            issues.append(ValidationIssue(
                Severity.CRITICAL,
                'DIAGNOSIS_MISSING',
                'At least one diagnosis code is required.',
                'diagnoses'
            ))
        
        if not claim.procedures:
            issues.append(ValidationIssue(
                Severity.CRITICAL,
                'PROCEDURES_MISSING',
                'At least one procedure is required.',
                'procedures'
            ))
        
        if claim.procedures and claim.claim_amount == 0:
            issues.append(ValidationIssue(
                Severity.HIGH,
                'CLAIM_AMOUNT_ZERO',
                'Total claim amount is $0. Check procedure charges.',
                'procedures'
            ))
        
        # ICD-10 validation (basic format)
        for i, diag in enumerate(claim.diagnoses):
            if not self._is_valid_icd10(diag.code):
                issues.append(ValidationIssue(
                    Severity.MEDIUM,
                    'INVALID_ICD10',
                    f'Diagnosis code "{diag.code}" may be invalid. ICD-10 codes should be in format like "M54.5".',
                    'diagnoses'
                ))
        
        # CPT validation (basic format)
        for i, proc in enumerate(claim.procedures):
            if not self._is_valid_cpt(proc.code):
                issues.append(ValidationIssue(
                    Severity.MEDIUM,
                    'INVALID_CPT',
                    f'Procedure code "{proc.code}" may be invalid. CPT codes should be 5 digits.',
                    'procedures'
                ))
        
        # Service date check
        if not claim.service_date:
            issues.append(ValidationIssue(
                Severity.HIGH,
                'SERVICE_DATE_MISSING',
                'Service date is required.',
                'claim'
            ))
        
        # Place of service check
        if not claim.place_of_service:
            issues.append(ValidationIssue(
                Severity.MEDIUM,
                'PLACE_OF_SERVICE_MISSING',
                'Place of service is recommended.',
                'claim'
            ))
        
        # Phone/contact check
        if not claim.patient.phone:
            issues.append(ValidationIssue(
                Severity.LOW,
                'PATIENT_PHONE_MISSING',
                'Patient phone number is not provided. This may delay processing.',
                'patient'
            ))
        
        # Calculate denial risk
        critical_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
        high_count = sum(1 for i in issues if i.severity == Severity.HIGH)
        medium_count = sum(1 for i in issues if i.severity == Severity.MEDIUM)
        
        # Risk scoring: CRITICAL issues heavily penalize
        risk_score = (critical_count * 40) + (high_count * 20) + (medium_count * 10)
        risk_score = min(int(risk_score), 100)
        
        # Determine risk level
        if risk_score >= 70:
            risk_level = "VERY HIGH"
        elif risk_score >= 50:
            risk_level = "HIGH"
        elif risk_score >= 30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            'issues': [i.to_dict() for i in issues],
            'issue_count': len(issues),
            'critical_count': critical_count,
            'high_count': high_count,
            'medium_count': medium_count,
            'denial_risk_score': risk_score,
            'denial_risk_level': risk_level,
            'is_valid': critical_count == 0,
        }
    
    @staticmethod
    def _is_valid_icd10(code: str) -> bool:
        """Validate ICD-10 code format"""
        # Format: Letter + 2 digits + . + 1-2 alphanumerics
        # Examples: M54.5, J45.901, Z23
        pattern = r'^[A-Z]\d{2}\.?[A-Z0-9]{0,2}$'
        return bool(re.match(pattern, code.upper()))
    
    @staticmethod
    def _is_valid_cpt(code: str) -> bool:
        """Validate CPT code format"""
        # 5 digits or letters/digits
        code_upper = code.upper()
        return len(code_upper) == 5 and code_upper.replace('-', '').isalnum()
