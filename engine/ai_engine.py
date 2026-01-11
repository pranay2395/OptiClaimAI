"""
Ollama AI Engine - Local LLM integration with graceful degradation
"""

import subprocess
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class OllamaEngine:
    """Interface to local Ollama for explanations"""
    
    def __init__(self, model: str = "llama2", timeout: int = 30):
        self.model = model
        self.timeout = timeout
        self.available = self._check_availability()
        
        if not self.available:
            logger.warning("Ollama not available - AI features will be disabled")
    
    def _check_availability(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                timeout=5,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"Ollama availability check failed: {e}")
            return False
    
    def explain_issue(self, issue_code: str, issue_message: str, claim_summary: str) -> Optional[str]:
        """Get AI explanation for a validation issue"""
        if not self.available:
            return None
        
        prompt = f"""You are a US Healthcare Billing & EDI Expert.

A claim has a validation issue:
Code: {issue_code}
Issue: {issue_message}

Claim context:
{claim_summary}

In 2-3 sentences, explain what this issue means in plain English and how a biller should fix it. 
Be practical, not academic. Do not use EDI jargon."""
        
        return self._query_ollama(prompt)
    
    def suggest_fixes(self, issues: list, claim_summary: str) -> Optional[str]:
        """Get AI suggestions for fixing multiple issues"""
        if not self.available:
            return None
        
        issues_text = "\n".join([f"- {i.get('message', '')}" for i in issues])
        
        prompt = f"""You are a US Healthcare Billing & EDI Expert.

A claim has these validation issues:
{issues_text}

Claim summary:
{claim_summary}

Provide 3-5 practical, actionable steps to fix these issues. Be specific.
Do not use EDI terminology."""
        
        return self._query_ollama(prompt)
    
    def summarize_claim(self, claim_summary: str) -> Optional[str]:
        """Generate a brief AI summary of the claim"""
        if not self.available:
            return None
        
        prompt = f"""You are a US Healthcare Billing & EDI Expert.

Summarize this claim in 2-3 sentences for a human biller:

{claim_summary}

Keep it simple and actionable."""
        
        return self._query_ollama(prompt)
    
    def _query_ollama(self, prompt: str) -> Optional[str]:
        """Run prompt against Ollama"""
        try:
            result = subprocess.run(
                ["ollama", "run", self.model, prompt],
                capture_output=True,
                timeout=self.timeout,
                text=True
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.warning(f"Ollama error: {result.stderr}")
                return None
        except subprocess.TimeoutExpired:
            logger.warning("Ollama query timed out")
            return None
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return None
