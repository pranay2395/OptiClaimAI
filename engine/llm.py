# engine/llm.py
import subprocess
import json
import shutil
import requests

def call_ollama(prompt: str, model: str = "llama3.1", timeout: int = 60) -> str:
    """
    Call Ollama via REST API (more reliable than subprocess).
    Connects to local Ollama server on localhost:11434
    """
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("response", "").strip()
        else:
            return f"Ollama error: HTTP {response.status_code}"
    
    except requests.exceptions.Timeout:
        return f"Ollama timed out after {timeout}s."
    
    except requests.exceptions.ConnectionError:
        return "Cannot connect to Ollama. Is 'ollama serve' running?"
    
    except Exception as e:
        return f"Ollama call failed: {str(e)}"

def call_online_ai(prompt: str, timeout: int = 15) -> str:
    """
    Fallback to free online AI services with multiple providers and better error handling.
    No API key required - uses publicly available models and services.
    """
    # List of free AI services to try
    services = [
        {
            "name": "Hugging Face GPT2",
            "url": "https://api-inference.huggingface.co/models/gpt2",
            "method": "hf"
        }
    ]
    
    for service in services:
        try:
            if service["method"] == "hf":
                # Hugging Face Inference API
                response = requests.post(
                    service["url"],
                    json={"inputs": prompt},
                    timeout=timeout,
                    headers={"User-Agent": "OptiClaimAI"}
                )
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        if isinstance(result, list) and len(result) > 0:
                            text = result[0].get("generated_text", "").strip()
                            if text and len(text) > len(prompt):
                                # Return only the generated part (after the prompt)
                                generated = text[len(prompt):].strip()
                                return generated if generated else text
                            elif text:
                                return text
                    except:
                        pass
        
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, Exception):
            continue
    
    # No online service worked - return empty string to trigger fallback
    return ""

def check_ollama() -> bool:
    """
    Check if Ollama is running and accessible via API.
    """
    try:
        response = requests.get(
            "http://localhost:11434/api/tags",
            timeout=3
        )
        return response.status_code == 200
    except:
        return False

def check_online_ai() -> bool:
    """
    Quick check if internet is available and online AI fallback can be reached.
    Tests basic connectivity to common services.
    """
    try:
        # Try to reach a simple, reliable endpoint
        response = requests.get(
            "https://www.google.com/search?q=test",
            timeout=3,
            headers={"User-Agent": "OptiClaimAI"}
        )
        # If we can reach the internet, online AI is likely available
        return response.status_code < 500
    except:
        # No internet or DNS failure
        return False

def explain_issue(issue: dict, parsed_claim: dict = None, raw_837: str = None) -> str:
    """
    Generate a natural-language explanation for a specific issue.
    Tries: Ollama (local) -> Online AI -> Smart template fallback
    Minimal prompt to avoid timeouts - does NOT include full claim data.
    """
    # Build minimal prompt
    issue_type = issue.get('issue_type', 'Unknown Issue')
    severity = issue.get('severity', 'Unknown')
    why_failed = issue.get('why_failed', 'Unknown')
    what_to_fix = issue.get('what_to_fix', 'Unknown')
    
    prompt = f"EDI Issue: {issue_type} ({severity}). Why: {why_failed}. Fix: {what_to_fix}?"
    
    # Try Ollama first (if available and responsive)
    if check_ollama():
        response = call_ollama(prompt, model="llama3.1", timeout=15)
        if response and "timed out" not in response.lower() and "error" not in response.lower():
            return response
    
    # Try online AI
    response = call_online_ai(prompt, timeout=10)
    if response and len(response) > 5:
        return response
    
    # Smart template fallback - construct explanation from rule data
    template = f"""**Issue:** {issue_type}

**Severity:** {severity}

**Why It Fails:** {why_failed}

**How to Fix:** {what_to_fix}

This issue will cause the claim to be rejected by the payer. Follow the suggested fix to resolve it."""
    
    return template