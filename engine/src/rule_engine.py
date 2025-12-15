"""Simple rule engine that supports condition handlers defined in rules.
Rules are JSON objects with `conditions` array. Each condition is dict with `type` and other fields.
"""
import json
from typing import List, Dict, Any


def load_rules(path: str) -> List[Dict[str, Any]]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


# Condition handler functions receive parsed_json and the cond dict, and return True when condition satisfied.
def _cond_txn_is(parsed: Dict, cond: Dict) -> bool:
    return parsed.get('transaction_type') == cond.get('value')


def _cond_claim_has_segment(parsed: Dict, cond: Dict) -> bool:
    seg = cond.get('segment')
    for c in parsed.get('claims', []):
        for s in c.get('segments', []):
            if s.get('tag') == seg:
                return True
    return False


def _cond_service_line_exists(parsed: Dict, cond: Dict) -> bool:
    return any(c.get('service_lines') for c in parsed.get('claims', []))


def _cond_amount_nonzero(parsed: Dict, cond: Dict) -> bool:
    for c in parsed.get('claims', []):
        clm = c.get('CLM', [])
        if len(clm) > 2:
            amt = clm[2]
            try:
                if float(amt) > 0:
                    return True
            except Exception:
                continue
    return False


def _cond_diagnosis_present(parsed: Dict, cond: Dict) -> bool:
    return any(c.get('diagnosis') for c in parsed.get('claims', []))


COND_HANDLERS = {
    'txn_is': _cond_txn_is,
    'claim_has_segment': _cond_claim_has_segment,
    'service_line_exists': _cond_service_line_exists,
    'amount_nonzero': _cond_amount_nonzero,
    'diagnosis_present': _cond_diagnosis_present,
}


def evaluate_rules(parsed_json: Dict[str, Any], rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings = []
    for r in rules:
        try:
            match = True
            for cond in r.get('conditions', []):
                typ = cond.get('type')
                handler = COND_HANDLERS.get(typ)
                if not handler:
                    # unknown condition: treat as non-match
                    match = False
                    break
                expected = cond.get('value', True)
                result = handler(parsed_json, cond)
                # If rule expects truthiness, require result==expected (for booleans)
                if isinstance(expected, bool):
                    if result != expected:
                        match = False
                        break
                else:
                    # for non-bool expected values, handler should implement comparison
                    if not result:
                        match = False
                        break
            if match:
                findings.append({'id': r.get('id'), 'severity': r.get('severity'), 'message': r.get('message'), 'fix': r.get('fix')})
        except Exception as e:
            findings.append({'id': r.get('id'), 'severity': 'error', 'message': f'rule_eval_error: {str(e)}', 'fix': ''})
    return findings
