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
        self.available = self._check_connection()
        
        if self.available:
            logger.info(f"✅ Connected to Ollama at {self.base_url}")
            self.available_models = self._fetch_models()
            logger.info(f"📦 Available models: {self.available_models}")
        else:
            logger.warning(f"❌ Cannot connect to Ollama at {self.base_url}")
            self.available_models = []
    
    def _check_connection(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
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
                models = [model['name'].split(':')[0] for model in data.get('models', [])]
                return list(set(models))  # Remove duplicates
        except Exception as e:
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
        
        Args:
            prompt: Input prompt
            model: Model name (e.g., 'llama3.1', 'glm-4', 'phi')
            stream: Whether to stream response
            temperature: Randomness (0.0-1.0)
            top_p: Nucleus sampling parameter
        
        Returns:
            Generated text or None if error
        """
        if not self.available:
            logger.error("Ollama not available")
            return None
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,  # We'll handle non-streaming for simplicity
                    "temperature": temperature,
                    "top_p": top_p,
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                logger.error(f"Ollama error: HTTP {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Ollama request timed out (>{self.timeout}s)")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Ollama")
            return None
        except Exception as e:
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
