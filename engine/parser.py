"""
EDI 837 Parser
Parses 837 Professional (837P) EDI files
"""

import re
from typing import Dict, List, Optional
from datetime import datetime
from .logger import setup_logger

logger = setup_logger(__name__)

class EDI837Parser:
    """Parser for 837 Professional EDI files"""

    def __init__(self):
        self.segments = []
        self.current_claim = None
        self.claims = []

    def parse(self, edi_content: str) -> Dict:
        """
        Parse EDI 837 file content

        Args:
            edi_content: Raw EDI file content

        Returns:
            Dictionary containing parsed claims and metadata
        """
        # Split into segments
        self.segments = self._split_segments(edi_content)

        # Parse file metadata
        metadata = self._parse_metadata()

        # Parse claims
        self.claims = self._parse_claims()

        return {
            'metadata': metadata,
            'claims': self.claims,
            'total_claims': len(self.claims)
        }

    def _split_segments(self, content: str) -> List[str]:
        """Split EDI content into segments"""
        # Remove whitespace and split by segment terminator
        content = content.strip()
        segments = content.split('~')
        return [seg.strip() for seg in segments if seg.strip()]

    def _parse_metadata(self) -> Dict:
        """Parse file-level metadata"""
        metadata = {}

        for segment in self.segments:
            elements = segment.split('*')

            if elements[0] == 'ISA':
                metadata['sender_id'] = elements[6].strip()
                metadata['receiver_id'] = elements[8].strip()
                metadata['interchange_date'] = elements[9]
                metadata['interchange_time'] = elements[10]

            elif elements[0] == 'GS':
                metadata['functional_group_date'] = elements[4]
                metadata['functional_group_time'] = elements[5]

            elif elements[0] == 'ST':
                metadata['transaction_set'] = elements[1]
                metadata['transaction_control'] = elements[2]

            elif elements[0] == 'BHT':
                metadata['transaction_purpose'] = elements[2]
                metadata['transaction_date'] = elements[4]

        return metadata

    def _parse_claims(self) -> List[Dict]:
        """Parse all claims from segments"""
        claims = []
        current_claim = None
        current_subscriber = None

        i = 0
        while i < len(self.segments):
            segment = self.segments[i]
            elements = segment.split('*')
            segment_id = elements[0]

            if segment_id == 'CLM':
                # Start new claim
                if current_claim:
                    claims.append(current_claim)

                current_claim = {
                    'claim_id': elements[1],
                    'claim_amount': float(elements[2]) if elements[2] else 0.0,
                    'place_of_service': elements[5].split(':')[0] if len(elements) > 5 else None,
                    'claim_frequency': elements[5].split(':')[1] if len(elements) > 5 and ':' in elements[5] else None,
                    'provider_signature': elements[6] if len(elements) > 6 else None,
                    'assignment_of_benefits': elements[7] if len(elements) > 7 else None,
                    'release_of_info': elements[8] if len(elements) > 8 else None,
                    'patient': {},
                    'provider': {},
                    'diagnoses': [],
                    'service_lines': []
                }

            elif segment_id == 'HI' and current_claim:
                # Diagnosis codes
                for j in range(1, len(elements)):
                    if elements[j]:
                        code_parts = elements[j].split(':')
                        if len(code_parts) >= 2:
                            current_claim['diagnoses'].append({
                                'code_type': code_parts[0],
                                'code': code_parts[1]
                            })

            elif segment_id == 'NM1' and current_claim:
                # Name segments - patient, subscriber, provider
                entity_type = elements[1] if len(elements) > 1 else None

                name_info = {
                    'entity_type': entity_type,
                    'name_last': elements[3] if len(elements) > 3 else None,
                    'name_first': elements[4] if len(elements) > 4 else None,
                    'id_qualifier': elements[8] if len(elements) > 8 else None,
                    'id_number': elements[9] if len(elements) > 9 else None
                }

                if entity_type == 'IL':  # Insured/Subscriber
                    current_subscriber = name_info
                    current_claim['patient'] = name_info
                elif entity_type == '85':  # Billing Provider
                    current_claim['provider'] = name_info

            elif segment_id == 'DMG' and current_claim:
                # Demographics
                current_claim['patient']['dob'] = elements[2] if len(elements) > 2 else None
                current_claim['patient']['gender'] = elements[3] if len(elements) > 3 else None

            elif segment_id == 'SV1' and current_claim:
                # Service line
                service_line = {
                    'procedure_code': elements[1].split(':')[1] if len(elements) > 1 and ':' in elements[1] else None,
                    'line_item_charge': float(elements[2]) if len(elements) > 2 and elements[2] else 0.0,
                    'unit_basis': elements[3] if len(elements) > 3 else None,
                    'service_units': float(elements[4]) if len(elements) > 4 and elements[4] else 0.0,
                    'diagnosis_pointer': elements[7] if len(elements) > 7 else None
                }
                current_claim['service_lines'].append(service_line)

            elif segment_id == 'DTP' and current_claim:
                # Date/Time - service date
                if len(elements) > 3:
                    qualifier = elements[1]
                    if qualifier == '472':  # Service date
                        current_claim['service_date'] = elements[3]

            i += 1

        # Add last claim
        if current_claim:
            claims.append(current_claim)

        return claims


# Legacy function for backward compatibility
def split_segments(raw: str) -> List[str]:
    if '~' in raw:
        raw = raw.replace('\r','')
        return [s.strip() for s in raw.split('~') if s.strip()]
    return [s.strip() for s in raw.splitlines() if s.strip()]


def detect_transaction_type(segments: List[str]) -> str:
    """Detect claim type based on service line segments."""
    if any(s.startswith('SV1') for s in segments):
        return 'professional'
    if any(s.startswith('SV2') for s in segments):
        return 'institutional'
    return 'unknown'


def parse_837(raw: str) -> Dict:
    """Parse 837 EDI file into structured format."""
    try:
        segments = split_segments(raw)
        logger.info(f"Parsed {len(segments)} segments from raw 837")

        parsed = {'claims': [], 'transaction_type': detect_transaction_type(segments)}
        current_claim = None

        for seg in segments:
            parts = seg.split('*')
            tag = parts[0]

            if tag == 'CLM':
                if current_claim:
                    parsed['claims'].append(current_claim)
                current_claim = {'CLM': parts, 'segments': []}
                # record the CLM segment itself
                current_claim.setdefault('segments', []).append({'tag': tag, 'parts': parts})
            elif tag in ('SV1','SV2'):
                if current_claim is None:
                    current_claim = {'CLM': [], 'segments': []}
                current_claim.setdefault('service_lines', []).append(parts)
            elif tag == 'HI':
                if current_claim is None:
                    current_claim = {'CLM': [], 'segments': []}
                current_claim.setdefault('diagnosis', []).append(parts)

            # record every segment in claim if claim exists
            if current_claim is not None:
                current_claim.setdefault('segments', []).append({'tag': tag, 'parts': parts})

        if current_claim:
            parsed['claims'].append(current_claim)

        logger.info(f"Successfully parsed {len(parsed['claims'])} claims, type: {parsed['transaction_type']}")
        return parsed
    except Exception as e:
        logger.error(f"Parsing failed: {str(e)}")
        return {'claims': [], 'transaction_type': 'unknown', 'error': str(e)}
