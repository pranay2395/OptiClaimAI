# engine/llm.py
import subprocess
import json

def call_ollama(prompt: str) -> str:
    """
    Call Ollama locally using subprocess.
    Uses llama3.1 model.
    """
    try:
        result = subprocess.run(
            ['ollama', 'run', 'llama3.1'],
            input=prompt,
            text=True,
            capture_output=True,
            timeout=60
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Error: {result.stderr.strip()}"
    except Exception as e:
        return f"Error: {str(e)}"

def explain_issue(issue: dict, parsed_claim: dict, raw_837: str) -> str:
    """
    Generate a natural-language explanation for a specific issue using Ollama.
    Builds an EDI-aware prompt referencing TR3, loops, segments, etc.
    """
    prompt = f"""
You are a US Healthcare EDI Expert specializing in 837 claims processing under TR3 standards.

Explain the following issue in natural language, referencing relevant loops, segments, elements, and payer rules where applicable.

Be deterministic-friendly and explainable. Focus on why this issue occurred and what it means for claim processing. Avoid hallucinating adjudication results.

Issue Details:
- Type: {issue.get('issue_type')}
- Severity: {issue.get('severity')}
- Message: {issue.get('why_failed')}
- Fix: {issue.get('what_to_fix')}
- Reference: {issue.get('reference')}

Parsed Claim Context (JSON):
{json.dumps(parsed_claim, indent=2)}

Raw 837 EDI Snippet (first 2000 characters):
{raw_837[:2000]}

Provide a clear, concise explanation of this issue and its implications.
"""
    return call_ollama(prompt)