# engine/rules_engine.py
import json, os
from typing import Dict, Any, List

RULES_DIR = os.path.join(os.path.dirname(__file__), 'rules')

_rules_cache = {}

def load_rules(scope='dhcs') -> List[Dict[str, Any]]:
    if scope in _rules_cache:
        return _rules_cache[scope]

    path = os.path.join(RULES_DIR, f'{scope}_rules.json')
    if not os.path.exists(path):
        _rules_cache[scope] = []
        return []

    with open(path, 'r') as f:
        rules = json.load(f)

    _rules_cache[scope] = rules
    return rules


def evaluate_rules(parsed_json: Dict[str, Any], rules: List[Dict[str, Any]]):
    findings = []

    for rule in rules:
        match = True

        for cond in rule.get('conditions', []):
            typ = cond.get('type')

            if typ == 'txn_is':
                match &= parsed_json.get('transaction_type') == cond.get('value')

            elif typ == 'claim_has_segment':
                seg = cond.get('segment')
                match &= any(
                    any(s.get('tag') == seg for s in (c.get('segments') or []))
                    for c in parsed_json.get('claims', [])
                )

            elif typ == 'service_line_exists':
                match &= any(c.get('service_lines') for c in parsed_json.get('claims', []))

            elif typ == 'amount_nonzero':
                match &= any(
                    c.get('CLM', [None, None, '0'])[2] not in ('0', None)
                    for c in parsed_json.get('claims', [])
                )

            elif typ == 'diagnosis_present':
                match &= any(c.get('diagnosis') for c in parsed_json.get('claims', []))

            if not match:
                break

        if match:
            findings.append({
                'issue_type': rule.get('id'),
                'severity': rule.get('severity', 'medium').capitalize(),
                'why_failed': rule.get('message'),
                'what_to_fix': rule.get('fix'),
                'reference': rule.get('id')
            })

    return findings
