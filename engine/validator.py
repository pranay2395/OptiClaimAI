"""
Claims Validation Engine
Validates parsed claims against comprehensive rules
"""

from typing import Dict, List, Optional
from .logger import setup_logger

logger = setup_logger(__name__)

class ClaimValidator:
    """Validator for healthcare claims"""

    def __init__(self):
        self.rules = self._load_validation_rules()

    def _load_validation_rules(self) -> Dict:
        """Load validation rules"""
        return {
            'required_fields': [
                'claim_id', 'claim_amount', 'service_lines'
            ],
            'field_validations': {
                'claim_amount': self._validate_claim_amount,
                'service_lines': self._validate_service_lines,
                'diagnoses': self._validate_diagnoses,
                'provider': self._validate_provider,
                'patient': self._validate_patient
            }
        }

    def validate_all(self, parsed_data: Dict) -> List[Dict]:
        """
        Validate all claims in parsed data

        Args:
            parsed_data: Parsed claims data

        Returns:
            List of validation results for each claim
        """
        claims = parsed_data.get('claims', [])
        results = []

        for i, claim in enumerate(claims):
            result = self.validate_single_claim(claim, i)
            results.append(result)

        logger.info(f"Validated {len(results)} claims")
        return results

    def validate_single_claim(self, claim: Dict, index: int) -> Dict:
        """
        Validate a single claim

        Args:
            claim: Single claim data
            index: Claim index for identification

        Returns:
            Validation result dictionary
        """
        errors = []
        warnings = []

        claim_id = claim.get('claim_id', f'Claim_{index + 1}')

        # Check required fields
        for field in self.rules['required_fields']:
            if not claim.get(field):
                errors.append(f"Missing required field: {field}")

        # Run field validations
        for field, validator_func in self.rules['field_validations'].items():
            field_errors, field_warnings = validator_func(claim.get(field))
            errors.extend(field_errors)
            warnings.extend(field_warnings)

        # Additional business rule validations
        business_errors, business_warnings = self._validate_business_rules(claim)
        errors.extend(business_errors)
        warnings.extend(business_warnings)

        return {
            'claim_id': claim_id,
            'errors': errors,
            'warnings': warnings,
            'is_valid': len(errors) == 0,
            'claim_data': claim
        }

    def _validate_claim_amount(self, amount: Optional[float]) -> tuple:
        """Validate claim amount"""
        errors = []
        warnings = []

        if amount is None:
            errors.append("Claim amount is missing")
        elif amount <= 0:
            errors.append("Claim amount must be positive")
        elif amount > 100000:  # Arbitrary high amount threshold
            warnings.append("Claim amount is unusually high")

        return errors, warnings

    def _validate_service_lines(self, service_lines: Optional[List]) -> tuple:
        """Validate service lines"""
        errors = []
        warnings = []

        if not service_lines:
            errors.append("No service lines found")
            return errors, warnings

        if len(service_lines) == 0:
            errors.append("Claim must have at least one service line")

        for i, line in enumerate(service_lines):
            line_num = i + 1

            if not line.get('procedure_code'):
                errors.append(f"Service line {line_num}: Missing procedure code")

            amount = line.get('line_item_charge', 0)
            if amount <= 0:
                errors.append(f"Service line {line_num}: Invalid charge amount")

            units = line.get('service_units', 0)
            if units <= 0:
                errors.append(f"Service line {line_num}: Invalid service units")

        return errors, warnings

    def _validate_diagnoses(self, diagnoses: Optional[List]) -> tuple:
        """Validate diagnosis codes"""
        errors = []
        warnings = []

        if not diagnoses:
            warnings.append("No diagnosis codes found")
            return errors, warnings

        if len(diagnoses) == 0:
            warnings.append("Claim should have at least one diagnosis code")

        # Check for valid ICD-10 format (basic check)
        for i, diag in enumerate(diagnoses):
            code = diag.get('code', '')
            if not code:
                errors.append(f"Diagnosis {i+1}: Missing diagnosis code")
            elif len(code) < 3:
                errors.append(f"Diagnosis {i+1}: Diagnosis code too short")

        return errors, warnings

    def _validate_provider(self, provider: Optional[Dict]) -> tuple:
        """Validate provider information"""
        errors = []
        warnings = []

        if not provider:
            errors.append("Provider information is missing")
            return errors, warnings

        if not provider.get('id_number'):
            errors.append("Provider ID number is missing")

        if not provider.get('name_last'):
            warnings.append("Provider last name is missing")

        return errors, warnings

    def _validate_patient(self, patient: Optional[Dict]) -> tuple:
        """Validate patient information"""
        errors = []
        warnings = []

        if not patient:
            errors.append("Patient information is missing")
            return errors, warnings

        if not patient.get('name_last'):
            warnings.append("Patient last name is missing")

        dob = patient.get('dob')
        if not dob:
            warnings.append("Patient date of birth is missing")
        else:
            # Basic DOB validation
            try:
                # Assume MMDDYY format
                if len(str(dob)) != 6:
                    warnings.append("Patient date of birth format may be invalid")
            except:
                warnings.append("Patient date of birth format is invalid")

        return errors, warnings

    def _validate_business_rules(self, claim: Dict) -> tuple:
        """Validate business rules"""
        errors = []
        warnings = []

        # Check if service lines have corresponding diagnoses
        service_lines = claim.get('service_lines', [])
        diagnoses = claim.get('diagnoses', [])

        if service_lines and not diagnoses:
            warnings.append("Service lines present but no diagnosis codes found")

        # Check for reasonable claim amount vs service lines
        total_service_amount = sum(
            line.get('line_item_charge', 0) * line.get('service_units', 1)
            for line in service_lines
        )
        claim_amount = claim.get('claim_amount', 0)

        if abs(total_service_amount - claim_amount) > 1.0:  # Allow small rounding differences
            warnings.append("Claim amount doesn't match sum of service line charges")

        # Check for duplicate procedure codes
        proc_codes = [line.get('procedure_code') for line in service_lines if line.get('procedure_code')]
        if len(proc_codes) != len(set(proc_codes)):
            warnings.append("Duplicate procedure codes found in service lines")

        return errors, warnings
