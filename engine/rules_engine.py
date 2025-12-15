# engine/rules_engine.py
import json, os
from typing import Dict, Any, List
import streamlit as st

RULES_DIR = os.path.join(os.path.dirname(__file__), 'rules')

@st.cache_data
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
            if match:
                sev_map = {'critical': 'High', 'high': 'High', 'medium': 'Medium', 'low': 'Low', 'info': 'Low'}
                severity = sev_map.get(rule.get('severity', 'medium'), 'Medium')
                findings.append({
                    'issue_type': rule.get('id', 'Unknown'),
                    'severity': severity,
                    'why_failed': rule.get('message', 'Rule failed'),
                    'what_to_fix': rule.get('fix', 'Fix the issue'),
                    'reference': rule.get('id', 'Rule reference')
                })
        except Exception as e:
            findings.append({
                'issue_type': 'Evaluation Error',
                'severity': 'Medium',
                'why_failed': f'Error evaluating rule: {str(e)}',
                'what_to_fix': 'Contact support',
                'reference': rule.get('id', 'Error')
            })
    return findings
