"""
Comprehensive Validation Engine
Deterministic rule-based claim validation with severity classification.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import date
from enum import Enum
import re


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class ValidationIssue:
    """Single validation issue"""
    field: str
    issue: str
    severity: ValidationSeverity
    fix_hint: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    """Complete validation result set"""
    is_valid: bool
    issues: List[ValidationIssue]
    denial_risk_score: float  # 0-100
    denial_risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "issues": [issue.to_dict() for issue in self.issues],
            "denial_risk_score": self.denial_risk_score,
            "denial_risk_level": self.denial_risk_level,
        }
    
    def has_high_severity_issues(self) -> bool:
        return any(issue.severity == ValidationSeverity.HIGH for issue in self.issues)


class ValidationEngine:
    """Healthcare claim validation engine"""
    
    def __init__(self):
        self.issues: List[ValidationIssue] = []
    
    def validate_claim(self, claim_dict: Dict[str, Any]) -> ValidationResult:
        """
        Validate a canonical claim (as dict).
        Returns ValidationResult with issues and risk score.
        """
        self.issues = []
        
        # Extract claim components
        patient = claim_dict.get("patient", {})
        provider = claim_dict.get("provider", {})
        service_lines = claim_dict.get("service_lines", [])
        diagnoses = claim_dict.get("diagnoses", [])
        payer = claim_dict.get("payer", {})
        
        # Run validation rules
        self._validate_patient(patient)
        self._validate_provider(provider)
        self._validate_service_lines(service_lines)
        self._validate_diagnoses(diagnoses)
        self._validate_payer(payer)
        self._validate_claim_structure(claim_dict)
        self._validate_dates(patient, service_lines)
        self._validate_amounts(service_lines)
        
        # Calculate denial risk
        denial_risk_score = self._calculate_denial_risk()
        denial_risk_level = self._assess_risk_level(denial_risk_score)
        
        is_valid = len([i for i in self.issues if i.severity == ValidationSeverity.HIGH]) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            issues=self.issues,
            denial_risk_score=denial_risk_score,
            denial_risk_level=denial_risk_level
        )
    
    def _validate_patient(self, patient: Dict[str, Any]) -> None:
        """Validate patient information"""
        if not patient.get("first_name"):
            self.issues.append(ValidationIssue(
                field="patient.first_name",
                issue="Patient first name is required",
                severity=ValidationSeverity.HIGH,
                fix_hint="Enter patient's first name"
            ))
        
        if not patient.get("last_name"):
            self.issues.append(ValidationIssue(
                field="patient.last_name",
                issue="Patient last name is required",
                severity=ValidationSeverity.HIGH,
                fix_hint="Enter patient's last name"
            ))
        
        if not patient.get("date_of_birth"):
            self.issues.append(ValidationIssue(
                field="patient.date_of_birth",
                issue="Patient date of birth is required",
                severity=ValidationSeverity.HIGH,
                fix_hint="Enter patient's DOB in YYYY-MM-DD format"
            ))
        else:
            try:
                dob = patient.get("date_of_birth")
                if isinstance(dob, str):
                    dob = date.fromisoformat(dob)
                
                # Check if patient is at least 0 years old
                today = date.today()
                age = (today - dob).days // 365
                if age < 0:
                    self.issues.append(ValidationIssue(
                        field="patient.date_of_birth",
                        issue="Patient date of birth cannot be in the future",
                        severity=ValidationSeverity.HIGH,
                        fix_hint="Verify patient's date of birth"
                    ))
                elif age > 150:
                    self.issues.append(ValidationIssue(
                        field="patient.date_of_birth",
                        issue="Patient age appears unrealistic (>150 years)",
                        severity=ValidationSeverity.MEDIUM,
                        fix_hint="Verify patient's date of birth"
                    ))
            except (ValueError, TypeError):
                self.issues.append(ValidationIssue(
                    field="patient.date_of_birth",
                    issue="Invalid date format for date of birth",
                    severity=ValidationSeverity.HIGH,
                    fix_hint="Use YYYY-MM-DD format"
                ))
        
        # Validate member ID format
        member_id = patient.get("member_id", "")
        if member_id and not re.match(r"^[A-Z0-9]{5,20}$", str(member_id)):
            self.issues.append(ValidationIssue(
                field="patient.member_id",
                issue="Member ID format appears invalid",
                severity=ValidationSeverity.MEDIUM,
                fix_hint="Member ID should be 5-20 alphanumeric characters"
            ))
    
    def _validate_provider(self, provider: Dict[str, Any]) -> None:
        """Validate provider information"""
        npi = str(provider.get("npi", "")).strip()
        
        if not npi:
            self.issues.append(ValidationIssue(
                field="provider.npi",
                issue="Provider NPI is required",
                severity=ValidationSeverity.HIGH,
                fix_hint="Enter a valid 10-digit NPI"
            ))
        elif not re.match(r"^[0-9]{10}$", npi):
            self.issues.append(ValidationIssue(
                field="provider.npi",
                issue="Provider NPI must be exactly 10 digits",
                severity=ValidationSeverity.HIGH,
                fix_hint="Enter a valid 10-digit NPI"
            ))
        
        # Validate NPI check digit (Luhn algorithm)
        if re.match(r"^[0-9]{10}$", npi):
            if not self._validate_npi_checksum(npi):
                self.issues.append(ValidationIssue(
                    field="provider.npi",
                    issue="NPI checksum validation failed",
                    severity=ValidationSeverity.MEDIUM,
                    fix_hint="Verify NPI is correct"
                ))
        
        if not provider.get("first_name"):
            self.issues.append(ValidationIssue(
                field="provider.first_name",
                issue="Provider first name is recommended",
                severity=ValidationSeverity.LOW,
                fix_hint="Enter provider's first name"
            ))
        
        if not provider.get("last_name"):
            self.issues.append(ValidationIssue(
                field="provider.last_name",
                issue="Provider last name is recommended",
                severity=ValidationSeverity.LOW,
                fix_hint="Enter provider's last name"
            ))
    
    def _validate_service_lines(self, service_lines: List[Dict[str, Any]]) -> None:
        """Validate service lines"""
        if not service_lines:
            self.issues.append(ValidationIssue(
                field="service_lines",
                issue="At least one service line is required",
                severity=ValidationSeverity.HIGH,
                fix_hint="Add at least one procedure/service"
            ))
            return
        
        for idx, line in enumerate(service_lines, 1):
            # Validate procedure code
            proc_code = str(line.get("procedure_code", "")).strip()
            if not proc_code:
                self.issues.append(ValidationIssue(
                    field=f"service_lines[{idx}].procedure_code",
                    issue="Procedure code is required",
                    severity=ValidationSeverity.HIGH,
                    fix_hint="Enter a valid CPT or HCPCS code"
                ))
            elif not re.match(r"^[A-Z0-9]{5,10}$", proc_code):
                self.issues.append(ValidationIssue(
                    field=f"service_lines[{idx}].procedure_code",
                    issue="Procedure code format appears invalid",
                    severity=ValidationSeverity.MEDIUM,
                    fix_hint="Procedure codes are 5-10 alphanumeric characters"
                ))
            
            # Validate service date
            service_date = line.get("service_date")
            if not service_date:
                self.issues.append(ValidationIssue(
                    field=f"service_lines[{idx}].service_date",
                    issue="Service date is required",
                    severity=ValidationSeverity.HIGH,
                    fix_hint="Enter service date in YYYY-MM-DD format"
                ))
            else:
                try:
                    if isinstance(service_date, str):
                        service_date = date.fromisoformat(service_date)
                    
                    today = date.today()
                    if service_date > today:
                        self.issues.append(ValidationIssue(
                            field=f"service_lines[{idx}].service_date",
                            issue="Service date cannot be in the future",
                            severity=ValidationSeverity.HIGH,
                            fix_hint="Verify service date"
                        ))
                    
                    if (today - service_date).days > 365:
                        self.issues.append(ValidationIssue(
                            field=f"service_lines[{idx}].service_date",
                            issue="Service date is more than 1 year in the past",
                            severity=ValidationSeverity.MEDIUM,
                            fix_hint="Very old claims may have submission deadline issues"
                        ))
                except (ValueError, TypeError):
                    self.issues.append(ValidationIssue(
                        field=f"service_lines[{idx}].service_date",
                        issue="Invalid service date format",
                        severity=ValidationSeverity.HIGH,
                        fix_hint="Use YYYY-MM-DD format"
                    ))
            
            # Validate charges
            line_charge = line.get("line_charge")
            if line_charge is None or line_charge == "":
                self.issues.append(ValidationIssue(
                    field=f"service_lines[{idx}].line_charge",
                    issue="Line charge is required",
                    severity=ValidationSeverity.HIGH,
                    fix_hint="Enter the charge amount"
                ))
            elif line_charge < 0:
                self.issues.append(ValidationIssue(
                    field=f"service_lines[{idx}].line_charge",
                    issue="Line charge cannot be negative",
                    severity=ValidationSeverity.HIGH,
                    fix_hint="Enter a positive charge amount"
                ))
            elif line_charge == 0:
                self.issues.append(ValidationIssue(
                    field=f"service_lines[{idx}].line_charge",
                    issue="Zero charge may indicate missing information",
                    severity=ValidationSeverity.MEDIUM,
                    fix_hint="Verify the charge amount"
                ))
            elif line_charge > 100000:
                self.issues.append(ValidationIssue(
                    field=f"service_lines[{idx}].line_charge",
                    issue="Charge amount is unusually high (>$100,000)",
                    severity=ValidationSeverity.MEDIUM,
                    fix_hint="Verify the charge amount"
                ))
    
    def _validate_diagnoses(self, diagnoses: List[Dict[str, Any]]) -> None:
        """Validate diagnosis codes"""
        if not diagnoses:
            self.issues.append(ValidationIssue(
                field="diagnoses",
                issue="At least one diagnosis is required",
                severity=ValidationSeverity.HIGH,
                fix_hint="Add at least one ICD-10 diagnosis code"
            ))
            return
        
        for idx, diag in enumerate(diagnoses, 1):
            icd_code = str(diag.get("icd10_code", "")).strip().upper()
            
            if not icd_code:
                self.issues.append(ValidationIssue(
                    field=f"diagnoses[{idx}].icd10_code",
                    issue="ICD-10 code is required",
                    severity=ValidationSeverity.HIGH,
                    fix_hint="Enter a valid ICD-10 diagnosis code (e.g., J45.901)"
                ))
            elif not self._is_valid_icd10_format(icd_code):
                self.issues.append(ValidationIssue(
                    field=f"diagnoses[{idx}].icd10_code",
                    issue="ICD-10 code format appears invalid",
                    severity=ValidationSeverity.MEDIUM,
                    fix_hint="ICD-10 codes are typically 5-7 characters with a decimal (e.g., J45.901)"
                ))
    
    def _validate_payer(self, payer: Dict[str, Any]) -> None:
        """Validate payer information"""
        payer_name = payer.get("payer_name", "").strip()
        payer_id = payer.get("payer_id", "").strip()
        
        if not payer_name and not payer_id:
            self.issues.append(ValidationIssue(
                field="payer",
                issue="Payer name or ID is recommended",
                severity=ValidationSeverity.LOW,
                fix_hint="Provide insurance company name or ANSI payer ID"
            ))
    
    def _validate_claim_structure(self, claim: Dict[str, Any]) -> None:
        """Validate overall claim structure"""
        required_fields = ["patient", "provider", "service_lines", "diagnoses"]
        for field in required_fields:
            if field not in claim or not claim[field]:
                self.issues.append(ValidationIssue(
                    field=field,
                    issue=f"Required field '{field}' is missing",
                    severity=ValidationSeverity.HIGH,
                    fix_hint=f"Add {field} information"
                ))
    
    def _validate_dates(self, patient: Dict[str, Any], service_lines: List[Dict[str, Any]]) -> None:
        """Cross-validate dates for consistency"""
        patient_dob = patient.get("date_of_birth")
        if not patient_dob:
            return
        
        try:
            if isinstance(patient_dob, str):
                patient_dob = date.fromisoformat(patient_dob)
            
            for idx, line in enumerate(service_lines, 1):
                service_date = line.get("service_date")
                if not service_date:
                    continue
                
                if isinstance(service_date, str):
                    service_date = date.fromisoformat(service_date)
                
                if service_date < patient_dob:
                    self.issues.append(ValidationIssue(
                        field=f"service_lines[{idx}].service_date",
                        issue="Service date is before patient's date of birth",
                        severity=ValidationSeverity.HIGH,
                        fix_hint="Verify service date and patient DOB"
                    ))
        except (ValueError, TypeError):
            pass  # Date validation already handled elsewhere
    
    def _validate_amounts(self, service_lines: List[Dict[str, Any]]) -> None:
        """Validate amount consistency"""
        for idx, line in enumerate(service_lines, 1):
            units = line.get("units")
            unit_price = line.get("unit_price")
            line_charge = line.get("line_charge")
            
            # If all three provided, verify math
            if units and unit_price and line_charge:
                try:
                    calculated = float(units) * float(unit_price)
                    expected = float(line_charge)
                    
                    # Allow 1 cent rounding tolerance
                    if abs(calculated - expected) > 0.01:
                        self.issues.append(ValidationIssue(
                            field=f"service_lines[{idx}].line_charge",
                            issue=f"Line charge math mismatch: {units} × ${unit_price:.2f} = ${calculated:.2f}, not ${expected:.2f}",
                            severity=ValidationSeverity.MEDIUM,
                            fix_hint="Verify units, unit price, and line charge"
                        ))
                except (ValueError, TypeError):
                    pass
    
    def _validate_npi_checksum(self, npi: str) -> bool:
        """Validate NPI checksum using Luhn algorithm"""
        if not re.match(r"^[0-9]{10}$", npi):
            return False
        
        # Add ISO/IEC 7064 prefix for NPI
        npi_full = "80840" + npi[:9]
        
        # Luhn algorithm
        digits = [int(d) for d in npi_full]
        checksum = 0
        for i, d in enumerate(digits):
            if i % 2 == 0:
                d = d * 2
                if d > 9:
                    d = d - 9
            checksum += d
        
        check_digit = (10 - (checksum % 10)) % 10
        return check_digit == int(npi[9])
    
    def _is_valid_icd10_format(self, code: str) -> bool:
        """Check if ICD-10 format is reasonable"""
        # ICD-10 format: Letter followed by digits, then dot, then more digits
        # Examples: J45.901, E11.9, M79.3
        return bool(re.match(r"^[A-Z][0-9]{1,2}(\.[0-9]{1,3})?$", code))
    
    def _calculate_denial_risk(self) -> float:
        """
        Calculate denial risk score (0-100) based on issues.
        HIGH severity issues = 20 points each
        MEDIUM severity issues = 10 points each
        LOW severity issues = 2 points each
        """
        score = 0.0
        for issue in self.issues:
            if issue.severity == ValidationSeverity.HIGH:
                score += 20
            elif issue.severity == ValidationSeverity.MEDIUM:
                score += 10
            elif issue.severity == ValidationSeverity.LOW:
                score += 2
        
        # Cap at 100
        return min(score, 100.0)
    
    def _assess_risk_level(self, score: float) -> str:
        """Convert risk score to risk level"""
        if score >= 80:
            return "CRITICAL"
        elif score >= 60:
            return "HIGH"
        elif score >= 40:
            return "MEDIUM"
        else:
            return "LOW"
