"""
Build canonical claims from various input sources
"""

from model.claim_schema import Patient, Provider, Diagnosis, Procedure, Claim
from engine.text_parser import parse_claim_from_text
from typing import Dict, Optional
from datetime import date
import logging

# Try to import EDI parser, but allow graceful failure
try:
    from engine.parser import EDI837Parser
except ImportError:
    EDI837Parser = None

logger = logging.getLogger(__name__)


class ClaimBuilder:
    """Build canonical claims from various sources"""
    
    @staticmethod
    def from_form(form_data: Dict) -> Claim:
        """Build from Streamlit form inputs"""
        
        # Parse service date
        service_date = form_data.get('service_date')
        if isinstance(service_date, str):
            from datetime import datetime
            service_date = datetime.fromisoformat(service_date).date()
        
        # Parse patient DOB
        patient_dob = form_data.get('patient_dob')
        if isinstance(patient_dob, str):
            from datetime import datetime
            patient_dob = datetime.fromisoformat(patient_dob).date()
        
        # Build claim
        claim = Claim(
            patient=Patient(
                first_name=form_data.get('patient_first_name', ''),
                last_name=form_data.get('patient_last_name', ''),
                date_of_birth=patient_dob,
                gender=form_data.get('patient_gender'),
                insurance_id=form_data.get('insurance_id'),
                group_number=form_data.get('group_number'),
                phone=form_data.get('patient_phone'),
                email=form_data.get('patient_email'),
            ),
            provider=Provider(
                first_name=form_data.get('provider_first_name', ''),
                last_name=form_data.get('provider_last_name', ''),
                npi=form_data.get('provider_npi', ''),
                specialty=form_data.get('provider_specialty'),
                phone=form_data.get('provider_phone'),
            ),
            diagnoses=[
                Diagnosis(code=d['code'], description=d.get('description'), primary=i==0)
                for i, d in enumerate(form_data.get('diagnoses', []))
            ],
            procedures=[
                Procedure(
                    code=p['code'],
                    units=float(p.get('units', 1)),
                    charge=float(p.get('charge', 0)),
                    modifiers=p.get('modifiers', [])
                )
                for p in form_data.get('procedures', [])
            ],
            service_date=service_date,
            place_of_service=form_data.get('place_of_service', '11'),
        )
        
        return claim
    
    @staticmethod
    def from_text(text: str) -> Optional[Claim]:
        """Build from free-text description"""
        try:
            parsed = parse_claim_from_text(text)
            if not parsed:
                return None
            
            # Extract required fields
            patient_data = parsed.get('patient', {})
            provider_data = parsed.get('provider', {})
            
            if not patient_data.get('first_name') or not provider_data.get('first_name'):
                return None
            
            claim = Claim(
                patient=Patient(
                    first_name=patient_data.get('first_name', ''),
                    last_name=patient_data.get('last_name', ''),
                    date_of_birth=patient_data.get('date_of_birth'),
                    insurance_id=patient_data.get('insurance_id'),
                ),
                provider=Provider(
                    first_name=provider_data.get('first_name', ''),
                    last_name=provider_data.get('last_name', ''),
                    npi=provider_data.get('npi', ''),
                    specialty=provider_data.get('specialty'),
                ),
                diagnoses=[
                    Diagnosis(code=d['code'], description=d.get('description'))
                    for d in parsed.get('diagnoses', [])
                ],
                procedures=[
                    Procedure(
                        code=p['code'],
                        charge=float(p.get('charge', 0))
                    )
                    for p in parsed.get('procedures', [])
                ],
                service_date=parsed.get('service_date'),
            )
            
            return claim
        except Exception as e:
            logger.error(f"Error parsing text: {e}")
            return None
    
    @staticmethod
    def from_edi(edi_content: str) -> Optional[Claim]:
        """Build from EDI 837 file"""
        if not EDI837Parser:
            logger.error("EDI parser not available")
            return None
        
        try:
            parser = EDI837Parser()
            parsed_data = parser.parse(edi_content)
            
            if not parsed_data or not parsed_data.get('claims'):
                return None
            
            # Convert first claim to canonical model
            claim_data = parsed_data['claims'][0]
            
            claim = Claim(
                patient=Patient(
                    first_name=claim_data.get('patient', {}).get('name_first', ''),
                    last_name=claim_data.get('patient', {}).get('name_last', ''),
                    date_of_birth=claim_data.get('patient', {}).get('dob'),
                    insurance_id=claim_data.get('patient', {}).get('id_number'),
                ),
                provider=Provider(
                    first_name=claim_data.get('provider', {}).get('name_first', ''),
                    last_name=claim_data.get('provider', {}).get('name_last', ''),
                    npi=claim_data.get('provider', {}).get('id_number', ''),
                ),
                diagnoses=[
                    Diagnosis(code=d.get('code', ''))
                    for d in claim_data.get('diagnoses', [])
                ],
                procedures=[
                    Procedure(
                        code=sl.get('procedure_code', ''),
                        charge=float(sl.get('line_item_charge', 0))
                    )
                    for sl in claim_data.get('service_lines', [])
                ],
                service_date=claim_data.get('service_date'),
                claim_amount=float(claim_data.get('claim_amount', 0)),
                claim_id=claim_data.get('claim_id'),
            )
            
            return claim
        except Exception as e:
            logger.error(f"Error parsing EDI: {e}")
            return None
