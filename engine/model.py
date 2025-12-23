# engine/model.py
import json
from pathlib import Path
from . import rules_engine as re_engine
from .llm import call_ollama
from .logger import setup_logger

logger = setup_logger(__name__)

# The prompts live at the repository root under `model/prompts`.
# `__file__` is `engine/model.py` so walk up two levels to reach the repo root.
PROMPT_TEMPLATE = Path(__file__).parent.parent.joinpath('model','prompts','base_prompt.txt').read_text()

def build_prompt(raw_837: str, parsed_json: dict, findings: list) -> str:
    instance = {
        "raw_837": raw_837[:4000],
        "parsed_json": parsed_json,
        "rule_findings": findings
    }
    prompt = PROMPT_TEMPLATE + "\n\nRULE_FINDINGS:\n" + json.dumps(findings, indent=2) + "\n\nINSTANCE_JSON:\n" + json.dumps(instance, indent=2)
    return prompt

def run_ollama(prompt: str, model: str = 'llama3.1') -> str:
    """Call Ollama via REST API (replaced subprocess with reliable implementation)."""
    logger.info(f"Calling Ollama with model {model}")
    response = call_ollama(prompt, model=model, timeout=90)
    if "error" in response.lower() or "timed out" in response.lower():
        logger.warning(f"Ollama call failed: {response}")
    else:
        logger.info("Ollama call succeeded")
    return response

def simple_heuristic_predict(parsed_json: dict, findings: list = None) -> dict:
    reasons = []
    prob = 5
    problem_segments = []
    fixes = []
    if findings:
        for f in findings:
            sev = f.get('severity')
            if sev == 'critical': prob += 50
            elif sev == 'high': prob += 25
            elif sev == 'medium': prob += 10
            elif sev == 'info': prob += 2
            reasons.append(f.get('message'))
            fixes.append(f.get('fix'))
            problem_segments.append({'loop':'unknown','segment':'N/A','element':'N/A','explain':f.get('message')})
    prob = min(prob, 95)
    return {'denial_probability': prob, 'reasons': reasons, 'problem_segments': problem_segments, 'fix_suggestions': fixes, 'corrected_837': ''}

def detect_claim_type(parsed_json: dict):
    if any(c.get('revenue_codes') for c in parsed_json.get('claims', [])):
        return "Institutional", "Revenue codes detected in claim data"
    return "Professional", "No revenue codes detected, defaulting to professional claim"

def compute_summary(issues: list, parsed_json: dict):
    total_claims = len(parsed_json.get('claims', []))
    invalid_claims = 1 if issues else 0
    invalid_percentage = 100 if invalid_claims else 0
    high_risk_issues = sum(1 for i in issues if i['severity'] == 'High')
    estimated_rework_cost = invalid_claims * 75
    return {
        'total_claims': total_claims,
        'invalid_claims': invalid_claims,
        'invalid_percentage': invalid_percentage,
        'high_risk_issues': high_risk_issues,
        'estimated_rework_cost': estimated_rework_cost
    }

def predict_denial(raw_837: str, parsed_json: dict) -> dict:
    try:
        logger.info("Starting denial prediction")
        rules = re_engine.load_rules('dhcs_comprehensive')
        issues = re_engine.evaluate_rules(parsed_json, rules)
        claim_type, claim_reason = detect_claim_type(parsed_json)
        summary = compute_summary(issues, parsed_json)
        dhcs_applied = 'CA' in str(parsed_json).upper() or 'MEDI-CAL' in str(parsed_json).upper()
        
        logger.info(f"Prediction complete: {claim_type} claim with {len(issues)} issues")
        
        return {
            'issues': issues,
            'claim_type': claim_type,
            'claim_reason': claim_reason,
            'summary': summary,
            'dhcs_applied': dhcs_applied
        }
    except Exception as e:
        logger.error(f"Error during prediction: {str(e)}")
        return {
            'issues': [{'issue_type': 'Processing Error', 'severity': 'High', 'why_failed': f'Error during prediction: {str(e)}', 'what_to_fix': 'Contact support', 'reference': 'Error'}],
            'claim_type': 'Unknown',
            'claim_reason': 'Error occurred',
            'summary': {'total_claims': 0, 'invalid_claims': 1, 'invalid_percentage': 100, 'high_risk_issues': 1, 'estimated_rework_cost': 75},
            'dhcs_applied': False
        }
