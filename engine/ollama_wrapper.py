"""
Ollama Wrapper - Reliable REST API integration
Fixes: wrong port, model discovery, streaming support
"""

import requests
import json
import logging
from typing import Optional, List, Dict, Generator
import os

logger = logging.getLogger(__name__)


class OllamaWrapper:
    """Reliable Ollama integration via REST API (port 11434)"""
    
    def __init__(self, host: str = "localhost", port: int = 11434):
        self.base_url = f"http://{host}:{port}"
        self.timeout = 120  # 2 minutes for long responses
        
        # DEBUG: Print the URL we are about to check
        print(f"🔍 [OllamaWrapper] Attempting to connect to Ollama at {self.base_url}")
        
        self.available = self._check_connection()
        
        if self.available:
            logger.info(f"✅ Connected to Ollama at {self.base_url}")
            self.available_models = self._fetch_models()
            # DEBUG: Confirm success and show models found
            print(f"✅ [OllamaWrapper] Connection successful. Available models: {self.available_models}")
        else:
            # DEBUG: Explicitly state the failure
            print(f"❌ [OllamaWrapper] FAILED to connect to Ollama at {self.base_url}")
            logger.warning(f"❌ Cannot connect to Ollama at {self.base_url}")
            self.available_models = []
    
    def _check_connection(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            # DEBUG: Print the exact endpoint being hit
            print(f"🔍 [OllamaWrapper] Sending GET request to {self.base_url}/api/tags")
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            # DEBUG: Print the response status code
            print(f"🔍 [OllamaWrapper] Response status code: {response.status_code}")
            return response.status_code == 200
        except requests.exceptions.ConnectionError as e:
            # DEBUG: This is the most common failure
            print(f"❌ [OllamaWrapper] Connection Error: Could not connect to Ollama. Is it running? Details: {e}")
            logger.debug(f"Ollama connection check failed: {e}")
            return False
        except Exception as e:
            # DEBUG: Catch any other unexpected errors
            print(f"❌ [OllamaWrapper] An unexpected error occurred during connection check: {e}")
            logger.debug(f"Ollama connection check failed: {e}")
            return False
    
    def _fetch_models(self) -> List[str]:
        """Get list of available models from Ollama"""
        if not self.available:
            return []
        
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                # FIX: Return the full model name instead of splitting it
                models = [model['name'] for model in data.get('models', [])]
                # The rest of this logic is fine
                return list(set(models))  # Remove duplicates
        except Exception as e:
            print(f"❌ [OllamaWrapper] Failed to fetch models: {e}")
            logger.error(f"Failed to fetch models: {e}")
        
        return []
    
    def generate(
        self,
        prompt: str,
        model: str = "llama3.1",
        stream: bool = False,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> Optional[str]:
        """
        Generate response from Ollama model
        """
        if not self.available:
            logger.error("Ollama not available for generation")
            return None
        
        try:
            # DEBUG: Log the generation attempt
            print(f"🤖 [OllamaWrapper] Generating with model '{model}'...")
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": temperature,
                    "top_p": top_p,
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                # DEBUG: Log generation failures
                print(f"❌ [OllamaWrapper] Generation error: HTTP {response.status_code} - {response.text}")
                logger.error(f"Ollama error: HTTP {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"❌ [OllamaWrapper] Generation timed out after {self.timeout}s")
            logger.error(f"Ollama request timed out (>{self.timeout}s)")
            return None
        except requests.exceptions.ConnectionError:
            print(f"❌ [OllamaWrapper] Connection lost during generation.")
            logger.error("Cannot connect to Ollama")
            return None
        except Exception as e:
            print(f"❌ [OllamaWrapper] An unexpected error occurred during generation: {e}")
            logger.error(f"Ollama error: {str(e)}")
            return None
    
    def generate_stream(
        self,
        prompt: str,
        model: str = "llama3.1",
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> Generator[str, None, None]:
        """Stream response from Ollama"""
        if not self.available:
            yield "❌ Ollama not available"
            return
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": True,
                    "temperature": temperature,
                    "top_p": top_p,
                },
                stream=True,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                yield chunk["response"]
                        except json.JSONDecodeError:
                            continue
            else:
                yield f"❌ Error: HTTP {response.status_code}"
                
        except Exception as e:
            yield f"❌ Error: {str(e)}"
    
    def embed(self, text: str, model: str = "llama3.1") -> Optional[List[float]]:
        """Generate embeddings for text"""
        if not self.available:
            return None
        
        try:
            response = requests.post(
                f"{self.base_url}/api/embed",
                json={
                    "model": model,
                    "input": text,
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("embeddings", [None])[0]
            
        except Exception as e:
            logger.error(f"Embedding error: {e}")
        
        return None
    
    def list_models(self) -> List[str]:
        """Get available models"""
        return self.available_models
    
    def is_available(self) -> bool:
        """Check if Ollama is available"""
        return self.available
    
    def health_check(self) -> Dict[str, any]:
        """Get health status"""
        return {
            "available": self.available,
            "url": self.base_url,
            "models": len(self.available_models),
            "model_list": self.available_models
        }


# Singleton instance
_ollama_instance = None


def get_ollama() -> OllamaWrapper:
    """Get or create Ollama singleton"""
    global _ollama_instance
    if _ollama_instance is None:
        _ollama_instance = OllamaWrapper()
    return _ollama_instance


def reset_ollama():
    """Reset Ollama connection (for reconnection)"""
    global _ollama_instance
    _ollama_instance = None
    return get_ollama()

