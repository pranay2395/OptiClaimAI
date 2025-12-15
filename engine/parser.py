import re
from typing import Dict, Any

def split_segments(raw: str):
    if '~' in raw:
        raw = raw.replace('\r','')
        segments = [s.strip() for s in raw.split('~') if s.strip()]
    else:
        segments = [s.strip() for s in raw.splitlines() if s.strip()]
    return segments

def parse_837(raw_text: str) -> Dict[str, Any]:
    segments = split_segments(raw_text)
    parsed = {"headers": [], "claims": []}
    current_claim = None

    for seg in segments:
        parts = seg.split('*')
        tag = parts[0]
        if tag == 'ST':
            parsed['transaction_set_control'] = parts[2] if len(parts) > 2 else ''
        elif tag == 'BHT':
            parsed['bht'] = parts[1:]
        elif tag == 'NM1' and len(parts)>1 and parts[1] == '85':
            parsed['billing_provider'] = {'name_elements': parts[2:]}
        elif tag == 'CLM':
            if current_claim:
                parsed['claims'].append(current_claim)
            current_claim = {"raw": seg, "CLM": parts}
        elif (tag == 'NM1' and len(parts)>1 and parts[1] == 'QC') or tag == 'PAT':
            if current_claim is None:
                current_claim = {"raw": "", "CLM": []}
            current_claim['patient'] = parts[2:]
        elif tag == 'REF':
            if current_claim is None:
                current_claim = {"raw": "", "CLM": []}
            current_claim.setdefault('refs', []).append(parts[1:])
        elif tag == 'HI':
            if current_claim is None:
                current_claim = {"raw": "", "CLM": []}
            current_claim.setdefault('diagnosis', []).append(parts[1:])
        elif tag == 'SV1' or tag == 'SV2':
            if current_claim is None:
                current_claim = {"raw": "", "CLM": []}
            current_claim.setdefault('service_lines', []).append(parts[1:])
        if current_claim is not None:
            current_claim.setdefault('segments', []).append({'tag': tag, 'parts': parts})
        else:
            parsed['headers'].append({'tag': tag, 'parts': parts})

    if current_claim:
        parsed['claims'].append(current_claim)
    return parsed
