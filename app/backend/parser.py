# app/backend/parser.py
import re
from typing import Dict, Any, List

def split_segments(raw: str) -> List[str]:
    if '~' in raw:
        raw = raw.replace('\r','')
        segments = [s.strip() for s in raw.split('~') if s.strip()]
    else:
        segments = [s.strip() for s in raw.splitlines() if s.strip()]
    return segments

def detect_transaction_type(segments: List[str]):
    """
    Prefer GS08 implementation id (005010X222 = 837P; 005010X223 = 837I).
    Fallback to presence of SV1 (professional) vs SV2 (institutional).
    """
    gs = [s for s in segments if s.startswith('GS*')]
    if gs:
        parts = gs[0].split('*')
        # GS structure: GS*{functional id}*sender*receiver*date*time*control*respons*version
        # version often in position 8 (index 8 if counting from 0)
        if len(parts) > 8:
            gs08 = parts[8]
            if '005010X222' in gs08:
                return 'professional', gs08
            if '005010X223' in gs08:
                return 'institutional', gs08
    # fallback by service line segments
    if any(s.startswith('SV1') for s in segments):
        return 'professional', ''
    if any(s.startswith('SV2') for s in segments):
        return 'institutional', ''
    return 'unknown', ''

def parse_837(raw_text: str) -> Dict[str, Any]:
    """
    Lightweight parser producing:
      - headers: other top segments
      - gs list
      - claims: list of claim dicts, each with CLM and service_lines, diagnosis, segments
      - transaction_type: 'professional'|'institutional'|'unknown'
    NOT a full X12 implementation parser; intended for rule checks and LLM context.
    """
    segments = split_segments(raw_text)
    parsed = {"headers": [], "gs": [], "claims": [], "transaction_type": None, "gs08": None}
    current_claim = None

    tx_type, gs08 = detect_transaction_type(segments)
    parsed['transaction_type'] = tx_type
    parsed['gs08'] = gs08

    for seg in segments:
        parts = seg.split('*')
        tag = parts[0]
        if tag == 'ST':
            parsed['transaction_set_control'] = parts[2] if len(parts) > 2 else ''
        elif tag == 'GS':
            parsed['gs'].append(parts[1:])
        elif tag == 'BHT':
            parsed['bht'] = parts[1:]
        elif tag == 'NM1' and len(parts)>1 and parts[1] == '85':
            parsed['billing_provider'] = {'name_elements': parts[2:]}
        elif tag == 'CLM':
            # commit previous claim
            if current_claim:
                parsed['claims'].append(current_claim)
            current_claim = {"raw": seg, "CLM": parts, "segments": []}
        elif (tag == 'NM1' and len(parts)>1 and parts[1] == 'QC') or tag == 'PAT':
            if current_claim is None:
                current_claim = {"raw":"", "CLM": [], "segments": []}
            current_claim['patient'] = parts[2:]
        elif tag == 'REF':
            if current_claim is None:
                current_claim = {"raw":"", "CLM": [], "segments": []}
            current_claim.setdefault('refs', []).append(parts[1:])
        elif tag == 'HI':
            if current_claim is None:
                current_claim = {"raw":"", "CLM": [], "segments": []}
            current_claim.setdefault('diagnosis', []).append(parts[1:])
        elif tag in ('SV1','SV2'):
            if current_claim is None:
                current_claim = {"raw":"", "CLM": [], "segments": []}
            current_claim.setdefault('service_lines', []).append({'tag':tag, 'parts':parts[1:]})
        # record segment
        if current_claim is not None:
            current_claim.setdefault('segments', []).append({'tag':tag, 'parts':parts})
        else:
            parsed['headers'].append({'tag':tag, 'parts':parts})

    if current_claim:
        parsed['claims'].append(current_claim)
    return parsed

if __name__ == "__main__":
    sample = "ISA*00*          *00*          *ZZ*SUBMITTER*ZZ*RECEIVER*251201*1253*^*00501*000000905*0*P*:~GS*HC*SENDER*RECEIVER*20251201*1253*1*X*005010X222~ST*837*0001~CLM*10001*150***11:B:1*Y*A*Y*I~SV1*HC:99214*150*UN*1***1~HI*ABK:Z23~SE*23*0001~IEA*1*000000905~"
    print(parse_837(sample))
