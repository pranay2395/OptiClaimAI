# engine/model.py
import json, subprocess
from pathlib import Path
from . import rules_engine as re_engine

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
    # On-prem: this calls local Ollama binary. You may swap for HTTP API if you run Ollama as a service.
    try:
        p = subprocess.run(['ollama', 'run', model], input=prompt.encode('utf-8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
        out = p.stdout.decode('utf-8').strip()
        return out or p.stderr.decode('utf-8').strip()
    except Exception as e:
        return json.dumps({'error':'ollama_call_failed','reason':str(e)})

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

def predict_denial(raw_837: str, parsed_json: dict, use_ollama: bool = True) -> dict:
    rules = re_engine.load_rules('dhcs')
    findings = re_engine.evaluate_rules(parsed_json, rules)
    # If there are critical errors, return immediate deterministic result
    if any(f.get('severity') == 'critical' for f in findings):
        out = simple_heuristic_predict(parsed_json, findings)
        out['rule_findings'] = findings
        return out
    prompt = build_prompt(raw_837, parsed_json, findings)
    if use_ollama:
        resp = run_ollama(prompt)
        try:
            data = json.loads(resp)
            if 'denial_probability' in data:
                data['rule_findings'] = findings
                return data
        except Exception:
            fallback = simple_heuristic_predict(parsed_json, findings)
            fallback['model_output'] = resp
            fallback['rule_findings'] = findings
            return fallback
    return simple_heuristic_predict(parsed_json, findings)
