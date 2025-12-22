# engine/llm.py
import subprocess
import json
import requests

def call_ollama(prompt: str) -> str:
    """
    Call Ollama via local REST API.
    Uses llama3.1 model.
    """
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.1",
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("response", "").strip()
        else:
            return f"Error: HTTP {response.status_code} - {response.text}"
    except requests.exceptions.RequestException as e:
        return f"Error: {str(e)}"

def check_ollama() -> bool:
    """
    Check if Ollama is running and accessible.
    """
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False
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