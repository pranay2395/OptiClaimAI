"""
Parse free-text claim descriptions into structured data
"""

import re
from typing import Optional, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def parse_claim_from_text(text: str) -> Optional[Dict]:
    """
    Parse free-text claim description into structured data.
    
    Example: "Patient John Doe, DOB 1985-01-15, insurance Blue Cross.
    Visit with Dr. Jane Smith (NPI 1234567890) on 2024-01-10.
    Diagnosis: M54.5 (back pain). Procedures: 99213 ($150), 71210 ($200)."
    """
    
    result = {
        'patient': {},
        'provider': {},
        'diagnoses': [],
        'procedures': [],
    }
    
    try:
        # Patient name - look for "Patient FirstName LastName"
        patient_match = re.search(r'[Pp]atient\s+([A-Za-z]+)\s+([A-Za-z]+)', text)
        if patient_match:
            result['patient'] = {
                'first_name': patient_match.group(1),
                'last_name': patient_match.group(2),
            }
        
        # Date of birth - multiple patterns
        dob_patterns = [
            r'[Dd]ate\s+of\s+[Bb]irth[:\s]*(\d{4}[-/]?\d{2}[-/]?\d{2})',
            r'DOB[:\s]*(\d{4}[-/]?\d{2}[-/]?\d{2})',
            r'(\d{4}[-/]?\d{2}[-/]?\d{2})',
        ]
        
        for pattern in dob_patterns:
            dob_match = re.search(pattern, text)
            if dob_match:
                try:
                    dob_str = dob_match.group(1).replace('/', '-')
                    result['patient']['date_of_birth'] = datetime.strptime(dob_str, '%Y-%m-%d').date()
                    break
                except:
                    continue
        
        # Insurance ID
        insurance_match = re.search(r'[Ii]nsurance\s+(?:ID|#)?[\s:]*([A-Z0-9]+)', text)
        if insurance_match:
            result['patient']['insurance_id'] = insurance_match.group(1)
        
        # Provider name - look for "Dr. FirstName LastName" or "Dr FirstName LastName"
        provider_match = re.search(r'(?:[Dd]r\.?\s+|[Ww]ith\s+)?([A-Za-z]+)\s+([A-Za-z]+)', text)
        if provider_match:
            result['provider'] = {
                'first_name': provider_match.group(1),
                'last_name': provider_match.group(2),
            }
        
        # Provider NPI - 10 consecutive digits
        npi_match = re.search(r'NPI[\s:]*(\d{10})', text)
        if npi_match:
            result['provider']['npi'] = npi_match.group(1)
        
        # Provider specialty
        specialty_match = re.search(r'[Ss]pecialty[\s:]*([A-Za-z\s]+?)(?:[,.]|$)', text)
        if specialty_match:
            result['provider']['specialty'] = specialty_match.group(1).strip()
        
        # Service date
        service_date_patterns = [
            r'on\s+(\d{4}[-/]?\d{2}[-/]?\d{2})',
            r'[Dd]ate[\s:]*(\d{4}[-/]?\d{2}[-/]?\d{2})',
            r'(\d{4}[-/]?\d{2}[-/]?\d{2})',
        ]
        
        for pattern in service_date_patterns:
            service_date_match = re.search(pattern, text)
            if service_date_match:
                try:
                    date_str = service_date_match.group(1).replace('/', '-')
                    result['service_date'] = datetime.strptime(date_str, '%Y-%m-%d').date()
                    break
                except:
                    continue
        
        # Diagnoses - look for ICD-10 codes (Letter + 2 digits + . + alphanumeric)
        diag_matches = re.findall(r'([A-Z]\d{2}\.\d[A-Z0-9]{0,1})\s*\(?([^)]*)\)?', text)
        result['diagnoses'] = [
            {'code': code.strip(), 'description': desc.strip() if desc else None}
            for code, desc in diag_matches
        ]
        
        # Procedures - look for CPT codes (5 digits or 5 alphanumeric) with optional charges
        # Pattern: code ($amount) or code amount
        proc_matches = re.findall(r'(\d{5}[A-Z]?|\b[A-Z]\d{4}\b)\s*\(?[\$]?([\d.]+)?\)?', text)
        result['procedures'] = [
            {'code': code.strip(), 'charge': float(charge) if charge else 0.0}
            for code, charge in proc_matches
            if code.strip()
        ]
        
        # Validate we got something useful
        if not result.get('patient', {}).get('first_name') and not result.get('provider', {}).get('first_name'):
            return None
        
        return result
    
    except Exception as e:
        logger.error(f"Error parsing text: {e}")
        return None
