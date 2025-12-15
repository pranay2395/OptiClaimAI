# engine/rules_engine.py
import json, os
from typing import Dict, Any, List

RULES_DIR = os.path.join(os.path.dirname(__file__), 'rules')

def load_rules(scope='dhcs') -> List[Dict[str, Any]]:
    path = os.path.join(RULES_DIR, f'{scope}_rules.json')
    if not os.path.exists(path):
        return []
    with open(path, 'r') as f:
        return json.load(f)

def evaluate_rules(parsed_json: Dict[str, Any], rules: List[Dict[str, Any]]):
    findings = []
    for rule in rules:
        try:
            match = True
            for cond in rule.get('conditions', []):
                typ = cond.get('type')
                if typ == 'txn_is':
                    if parsed_json.get('transaction_type') != cond.get('value'):
                        match = False; break
                elif typ == 'claim_has_segment':
                    seg = cond.get('segment')
                    found = any(any(s.get('tag')==seg for s in (c.get('segments') or [])) for c in parsed_json.get('claims', []))
                    if not found:
                        match = False; break
                elif typ == 'service_line_exists':
                    found = any(c.get('service_lines') for c in parsed_json.get('claims', []))
                    if cond.get('value') and not found:
                        match = False; break
                elif typ == 'amount_nonzero':
                    found_nonzero = False
                    for c in parsed_json.get('claims', []):
                        clm = c.get('CLM', [])
                        if len(clm) > 2 and clm[2] and clm[2] != '0':
                            found_nonzero = True
                    if cond.get('value') and not found_nonzero:
                        match = False; break
                elif typ == 'diagnosis_present':
                    found = any(c.get('diagnosis') for c in parsed_json.get('claims', []))
                    if cond.get('value') and not found:
                        match = False; break
                # add additional cond handlers as needed
            if match:
                findings.append({'id': rule.get('id'), 'severity': rule.get('severity'), 'message': rule.get('message'), 'fix': rule.get('fix')})
        except Exception as e:
            findings.append({'id': rule.get('id'), 'severity':'error', 'message':f'rule_eval_error: {str(e)}', 'fix': ''})
    return findings
