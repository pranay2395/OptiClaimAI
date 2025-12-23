"""Simple 837 parser.
Produces a dict with `claims`, `transaction_type`, and basic segment lists.
"""
from typing import List, Dict
from .logger import setup_logger

logger = setup_logger(__name__)


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
