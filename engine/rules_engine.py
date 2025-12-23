# engine/rules_engine.py
import json, os
from typing import Dict, Any, List
from .logger import setup_logger

logger = setup_logger(__name__)

RULES_DIR = os.path.join(os.path.dirname(__file__), 'rules')

_rules_cache = {}

def load_rules(scope='dhcs_comprehensive') -> List[Dict[str, Any]]:
    """Load rules from comprehensive ruleset. Falls back to dhcs_rules if comprehensive not found."""
    if scope in _rules_cache:
        return _rules_cache[scope]

    # Try comprehensive first, fallback to dhcs
    path = os.path.join(RULES_DIR, f'{scope}_rules.json')
    if not os.path.exists(path):
        path = os.path.join(RULES_DIR, 'dhcs_rules.json')
    
    if not os.path.exists(path):
        logger.warning(f"No rules file found at {path}")
        _rules_cache[scope] = []
        return []

    with open(path, 'r', encoding='utf-8') as f:
        rules = json.load(f)

    logger.info(f"Loaded {len(rules)} rules from {os.path.basename(path)}")
    _rules_cache[scope] = rules
    return rules


def evaluate_rules(parsed_json: Dict[str, Any], rules: List[Dict[str, Any]]):
    findings = []

    for rule in rules:
        match = True

        for cond in rule.get('conditions', []):
            typ = cond.get('type')
            expected = cond.get('value', True)  # Default to True if not specified

            if typ == 'txn_is':
                result = parsed_json.get('transaction_type') == cond.get('value')
                match &= result

            elif typ == 'claim_has_segment':
                seg = cond.get('segment')
                result = any(
                    any(s.get('tag') == seg for s in (c.get('segments') or []))
                    for c in parsed_json.get('claims', [])
                )
                # Handle inverted logic: if expected=False, negate result
                if isinstance(expected, bool):
                    result = result if expected else not result
                match &= result

            elif typ == 'claim_missing_segment':
                # Direct handler for missing segment (clearer than value=false)
                seg = cond.get('segment')
                result = not any(
                    any(s.get('tag') == seg for s in (c.get('segments') or []))
                    for c in parsed_json.get('claims', [])
                )
                match &= result

            elif typ == 'service_line_exists':
                result = any(c.get('service_lines') for c in parsed_json.get('claims', []))
                match &= result

            elif typ == 'amount_nonzero':
                result = any(
                    c.get('CLM', [None, None, '0'])[2] not in ('0', None)
                    for c in parsed_json.get('claims', [])
                )
                if isinstance(expected, bool):
                    result = result if expected else not result
                match &= result

            elif typ == 'diagnosis_present':
                result = any(c.get('diagnosis') for c in parsed_json.get('claims', []))
                if isinstance(expected, bool):
                    result = result if expected else not result
                match &= result

            elif typ == 'transaction_header_valid':
                # Check if ST segment exists and has '837' as first element
                st_segments = [s for c in parsed_json.get('claims', []) 
                              for s in c.get('segments', []) if s.get('tag') == 'ST']
                result = any(s.get('parts', [None, ''])[1] == '837' for s in st_segments) if st_segments else False
                match &= result

            elif typ == 'npi_valid':
                # Check for valid NPI (10 digits)
                result = any(
                    len(str(c.get('provider_npi', ''))) == 10
                    for c in parsed_json.get('claims', [])
                )
                match &= result

            elif typ == 'diagnosis_to_procedure_valid':
                # Check that diagnosis and procedures exist and align
                result = any(
                    c.get('diagnosis') and c.get('service_lines')
                    for c in parsed_json.get('claims', [])
                )
                match &= result

            elif typ == 'age_appropriate_procedure':
                # Placeholder: assumes age validation data would be available
                result = True  # Default to passing unless specific age check logic added
                match &= result

            elif typ == 'bill_type_present':
                # Check for UB-04 bill type in institutional claims
                result = parsed_json.get('transaction_type') != 'institutional' or any(
                    any(s.get('tag') == 'UB' for s in c.get('segments', []))
                    for c in parsed_json.get('claims', [])
                )
                match &= result

            elif typ == 'provider_identified':
                # Check for provider loop existence
                result = any(
                    c.get('provider_npi') or any(s.get('tag') == 'NM1' for s in c.get('segments', []))
                    for c in parsed_json.get('claims', [])
                )
                match &= result

            elif typ == 'subscriber_identified':
                # Check for subscriber information
                result = any(
                    c.get('subscriber_id') or any(s.get('tag') in ('NM1', 'DMG') for s in c.get('segments', []))
                    for c in parsed_json.get('claims', [])
                )
                match &= result

            elif typ == 'place_of_service_valid':
                # Check for valid POS code
                valid_pos = {'01', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', 
                            '22', '23', '24', '25', '26', '27', '28', '29', '30', '31', '32', '33',
                            '34', '35', '36', '37', '38', '39', '40', '41', '42', '43', '44', '45',
                            '46', '47', '48', '49', '50', '51', '52', '53', '54', '55', '56', '57',
                            '58', '59', '60', '61'}
                result = True  # Default to True if POS validation not yet implemented
                match &= result

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
            logger.debug(f"Rule matched: {rule.get('id')} - {rule.get('message')}")
    
    logger.info(f"Evaluated {len(rules)} rules, found {len(findings)} issues")
    return findings
