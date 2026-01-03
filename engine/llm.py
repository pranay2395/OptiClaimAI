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
    Generate a detailed, natural-language explanation for a specific issue.
    Enhanced prompts for more comprehensive responses.
    Tries: Ollama (local) -> Online AI -> Smart template fallback
    """
    # Build detailed prompt with context
    issue_type = issue.get('issue_type', 'Unknown Issue')
    severity = issue.get('severity', 'Unknown')
    why_failed = issue.get('why_failed', 'Unknown')
    what_to_fix = issue.get('what_to_fix', 'Unknown')
    reference = issue.get('reference', 'Unknown')

    # Enhanced prompt with more context and structure
    prompt = f"""As a healthcare claims expert, explain this EDI claim validation issue in detail:

ISSUE DETAILS:
- Issue Type: {issue_type}
- Severity Level: {severity}
- Why It Failed: {why_failed}
- How to Fix: {what_to_fix}
- Reference: {reference}

Please provide a comprehensive explanation that includes:
1. What this issue means for claim processing
2. Why payers reject claims for this reason
3. Step-by-step instructions for fixing it
4. Potential impact on reimbursement
5. Best practices to prevent this issue

Keep the explanation clear, professional, and actionable."""

    # Try Ollama first (if available and responsive)
    if check_ollama():
        response = call_ollama(prompt, model="llama3.1", timeout=30)  # Increased timeout
        if response and "timed out" not in response.lower() and "error" not in response.lower():
            return response

    # Try online AI with enhanced prompt
    response = call_online_ai(prompt, timeout=15)  # Increased timeout
    if response and len(response) > 10:  # Require longer response
        return response

    # Enhanced smart template fallback with more detail
    severity_impact = {
        'critical': 'will completely prevent payment and may result in claim rejection',
        'high': 'will likely cause delays and potential payment reductions',
        'medium': 'may cause processing delays or require manual review',
        'low': 'is a minor issue but should be corrected for best practices'
    }

    impact = severity_impact.get(severity.lower(), 'may affect claim processing')

    template = f"""## 🔍 Detailed Issue Analysis: {issue_type}

### **Issue Severity:** {severity.upper()}
**Impact:** This {impact}.

### **What This Issue Means**
{why_failed}

This type of error commonly occurs in healthcare claims processing and indicates a problem with the claim data formatting or content that prevents proper adjudication by the payer system.

### **Why Payers Reject Claims for This Reason**
Payers have automated systems that validate claims against strict EDI standards. When this specific issue is detected, the claim cannot be processed through the normal workflow and may be:
- Rejected outright
- Placed in a manual review queue (increasing processing time)
- Subject to payment delays or reductions

### **Step-by-Step Fix Instructions**
{what_to_fix}

**Technical Details:**
- **EDI Reference:** {reference}
- **Affected Segment/Element:** This typically involves the claim header or service line data
- **Validation Rule:** Automated systems check for this condition during the initial parsing phase

### **Potential Impact on Reimbursement**
- **Payment Delays:** 15-45 days additional processing time
- **Reduced Payment:** Up to 20% reduction for non-compliant claims
- **Administrative Burden:** Manual follow-up required
- **Patient Impact:** Delayed care authorization if applicable

### **Best Practices to Prevent This Issue**
1. **Validate claims before submission** using automated tools
2. **Train billing staff** on proper EDI formatting requirements
3. **Implement automated checks** in your practice management system
4. **Regularly audit** submitted claims for common errors
5. **Stay updated** on payer-specific requirements and EDI standards

### **Quick Reference**
- **Error Code:** {reference}
- **Resolution Time:** 1-2 business days with correct fix
- **Appeals Process:** Required if claim is incorrectly rejected

**Note:** Always verify the fix with your specific payer guidelines, as requirements may vary slightly between insurance companies and government programs."""

    return template
