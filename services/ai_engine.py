"""
AI Explanation Engine
Optional local-first AI (Ollama) with fallback to API keys.
Graceful degradation if AI unavailable.
"""

import requests
from typing import Optional, Dict, Any
import os
import json
from datetime import datetime


class AIEngine:
    """Local-first AI engine with optional API key fallback"""
    
    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama2")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self._cache: Dict[str, str] = {}
    
    def is_available(self, provider: str = "ollama") -> bool:
        """Check if AI provider is available"""
        if provider == "ollama":
            return self._check_ollama_available()
        elif provider == "openai":
            return bool(self.openai_api_key)
        elif provider == "anthropic":
            return bool(self.anthropic_api_key)
        return False
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            return response.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            return False
    
    def explain_issues(self, issues: list, claim_dict: Dict[str, Any]) -> Optional[str]:
        """
        Generate human-readable explanation of validation issues.
        Falls back gracefully if AI unavailable.
        """
        # Check cache first
        cache_key = self._get_cache_key("explain_issues", issues)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Try Ollama first (local, private, no API key needed)
        if self.is_available("ollama"):
            result = self._explain_via_ollama(issues, claim_dict)
            if result:
                self._cache[cache_key] = result
                return result
        
        # Try OpenAI
        if self.is_available("openai"):
            result = self._explain_via_openai(issues, claim_dict)
            if result:
                self._cache[cache_key] = result
                return result
        
        # Try Anthropic
        if self.is_available("anthropic"):
            result = self._explain_via_anthropic(issues, claim_dict)
            if result:
                self._cache[cache_key] = result
                return result
        
        # Fallback: Generate basic explanation without AI
        return self._basic_explanation(issues)
    
    def suggest_fixes(self, issues: list) -> Optional[str]:
        """
        Generate step-by-step fix suggestions.
        """
        cache_key = self._get_cache_key("suggest_fixes", issues)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if self.is_available("ollama"):
            result = self._suggest_via_ollama(issues)
            if result:
                self._cache[cache_key] = result
                return result
        
        if self.is_available("openai"):
            result = self._suggest_via_openai(issues)
            if result:
                self._cache[cache_key] = result
                return result
        
        # Fallback
        return self._basic_suggestions(issues)
    
    def answer_question(self, question: str, claim_dict: Dict[str, Any]) -> Optional[str]:
        """
        Answer user questions about the claim.
        """
        if not self.is_available("ollama") and not self.is_available("openai") and not self.is_available("anthropic"):
            return "AI is not available. Please check if Ollama is running or provide an API key."
        
        if self.is_available("ollama"):
            return self._answer_via_ollama(question, claim_dict)
        
        if self.is_available("openai"):
            return self._answer_via_openai(question, claim_dict)
        
        return None
    
    def _explain_via_ollama(self, issues: list, claim_dict: Dict[str, Any]) -> Optional[str]:
        """Get issue explanation from Ollama"""
        try:
            issues_text = "\n".join([
                f"- {issue.get('issue', 'Unknown')} (Severity: {issue.get('severity', 'UNKNOWN')})"
                for issue in issues
            ])
            
            prompt = f"""A healthcare claim was submitted with the following validation issues:

{issues_text}

Patient: {claim_dict.get('patient', {}).get('first_name')} {claim_dict.get('patient', {}).get('last_name')}
Provider: {claim_dict.get('provider', {}).get('first_name')} {claim_dict.get('provider', {}).get('last_name')}

Please explain in simple, non-technical language what these issues mean and why they might cause claim denial."""
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3,  # Low temperature for consistency
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
        except Exception as e:
            print(f"Ollama error: {e}")
        
        return None
    
    def _explain_via_openai(self, issues: list, claim_dict: Dict[str, Any]) -> Optional[str]:
        """Get issue explanation from OpenAI"""
        try:
            from openai import OpenAI
            
            issues_text = "\n".join([
                f"- {issue.get('issue', 'Unknown')} (Severity: {issue.get('severity', 'UNKNOWN')})"
                for issue in issues
            ])
            
            prompt = f"""A healthcare claim was submitted with the following validation issues:

{issues_text}

Patient: {claim_dict.get('patient', {}).get('first_name')} {claim_dict.get('patient', {}).get('last_name')}
Provider: {claim_dict.get('provider', {}).get('first_name')} {claim_dict.get('provider', {}).get('last_name')}

Please explain in simple, non-technical language what these issues mean and why they might cause claim denial."""
            
            client = OpenAI(api_key=self.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI error: {e}")
        
        return None
    
    def _explain_via_anthropic(self, issues: list, claim_dict: Dict[str, Any]) -> Optional[str]:
        """Get issue explanation from Anthropic"""
        try:
            import anthropic
            
            issues_text = "\n".join([
                f"- {issue.get('issue', 'Unknown')} (Severity: {issue.get('severity', 'UNKNOWN')})"
                for issue in issues
            ])
            
            prompt = f"""A healthcare claim was submitted with the following validation issues:

{issues_text}

Patient: {claim_dict.get('patient', {}).get('first_name')} {claim_dict.get('patient', {}).get('last_name')}
Provider: {claim_dict.get('provider', {}).get('first_name')} {claim_dict.get('provider', {}).get('last_name')}

Please explain in simple, non-technical language what these issues mean and why they might cause claim denial."""
            
            client = anthropic.Anthropic(api_key=self.anthropic_api_key)
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
        except Exception as e:
            print(f"Anthropic error: {e}")
        
        return None
    
    def _suggest_via_ollama(self, issues: list) -> Optional[str]:
        """Get fix suggestions from Ollama"""
        try:
            issues_text = "\n".join([
                f"- {issue.get('fix_hint', 'Fix needed')}"
                for issue in issues
            ])
            
            prompt = f"""Based on these healthcare claim validation issues:

{issues_text}

Provide step-by-step instructions to fix these issues. Be specific and actionable."""
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3,
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
        except Exception as e:
            print(f"Ollama error: {e}")
        
        return None
    
    def _suggest_via_openai(self, issues: list) -> Optional[str]:
        """Get fix suggestions from OpenAI"""
        try:
            from openai import OpenAI
            
            issues_text = "\n".join([
                f"- {issue.get('fix_hint', 'Fix needed')}"
                for issue in issues
            ])
            
            prompt = f"""Based on these healthcare claim validation issues:

{issues_text}

Provide step-by-step instructions to fix these issues. Be specific and actionable."""
            
            client = OpenAI(api_key=self.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI error: {e}")
        
        return None
    
    def _answer_via_ollama(self, question: str, claim_dict: Dict[str, Any]) -> Optional[str]:
        """Answer question via Ollama"""
        try:
            patient_name = f"{claim_dict.get('patient', {}).get('first_name')} {claim_dict.get('patient', {}).get('last_name')}"
            prompt = f"""You are a healthcare claims expert. Answer this question about a claim:

Claim Patient: {patient_name}
Question: {question}

Answer in simple, clear language."""
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3,
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
        except Exception as e:
            print(f"Ollama error: {e}")
        
        return None
    
    def _answer_via_openai(self, question: str, claim_dict: Dict[str, Any]) -> Optional[str]:
        """Answer question via OpenAI"""
        try:
            from openai import OpenAI
            
            patient_name = f"{claim_dict.get('patient', {}).get('first_name')} {claim_dict.get('patient', {}).get('last_name')}"
            prompt = f"""You are a healthcare claims expert. Answer this question about a claim:

Claim Patient: {patient_name}
Question: {question}

Answer in simple, clear language."""
            
            client = OpenAI(api_key=self.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI error: {e}")
        
        return None
    
    def _basic_explanation(self, issues: list) -> str:
        """Generate basic explanation without AI"""
        high_severity = [i for i in issues if i.get("severity") == "HIGH"]
        medium_severity = [i for i in issues if i.get("severity") == "MEDIUM"]
        low_severity = [i for i in issues if i.get("severity") == "LOW"]
        
        explanation = []
        
        if high_severity:
            explanation.append("**Critical Issues (Must Fix):**")
            for issue in high_severity:
                explanation.append(f"- {issue.get('issue', 'Unknown issue')}")
        
        if medium_severity:
            explanation.append("\n**Medium Priority Issues:**")
            for issue in medium_severity:
                explanation.append(f"- {issue.get('issue', 'Unknown issue')}")
        
        if low_severity:
            explanation.append("\n**Low Priority Issues:**")
            for issue in low_severity:
                explanation.append(f"- {issue.get('issue', 'Unknown issue')}")
        
        if not explanation:
            return "No issues found."
        
        return "\n".join(explanation)
    
    def _basic_suggestions(self, issues: list) -> str:
        """Generate basic suggestions without AI"""
        suggestions = ["**Steps to Fix Issues:**\n"]
        for idx, issue in enumerate(issues, 1):
            suggestions.append(f"{idx}. {issue.get('fix_hint', 'Review and correct this issue')}")
        
        return "\n".join(suggestions)
    
    def _get_cache_key(self, action: str, data: Any) -> str:
        """Generate cache key for AI responses"""
        import hashlib
        data_str = json.dumps(data, default=str, sort_keys=True)
        hash_obj = hashlib.md5(data_str.encode())
        return f"{action}_{hash_obj.hexdigest()}"
