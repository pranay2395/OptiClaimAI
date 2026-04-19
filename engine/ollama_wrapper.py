"""
Small, resilient wrapper around the Ollama HTTP API.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Generator, List, Optional

import requests

logger = logging.getLogger(__name__)


class OllamaWrapper:
    """Reliable Ollama integration via the local REST API."""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        resolved_host = host or os.getenv("OLLAMA_HOST", "127.0.0.1")
        resolved_port = int(port or os.getenv("OLLAMA_PORT", "11434"))
        self.base_url = f"http://{resolved_host}:{resolved_port}"
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "90"))
        self.available = False
        self.available_models: List[str] = []
        self.refresh()

    def refresh(self) -> bool:
        """Refresh connection status and model list."""
        self.available = self._check_connection()
        self.available_models = self._fetch_models() if self.available else []
        return self.available

    def _check_connection(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.ok
        except requests.RequestException as exc:
            logger.debug("Ollama connection check failed: %s", exc)
            return False

    def _fetch_models(self) -> List[str]:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            data = response.json()
            models = [model.get("name") for model in data.get("models", []) if model.get("name")]
            return sorted(set(models))
        except requests.RequestException as exc:
            logger.warning("Failed to fetch Ollama models: %s", exc)
            return []

    def _resolve_model(self, model: Optional[str]) -> Optional[str]:
        if not self.available:
            return None
        if not self.available_models:
            self.available_models = self._fetch_models()
        if model and model in self.available_models:
            return model
        if self.available_models:
            return self.available_models[0]
        return model

    def generate(
        self,
        prompt: str,
        model: str = "llama3.1",
        stream: bool = False,
        temperature: float = 0.3,
        top_p: float = 0.9,
    ) -> Optional[str]:
        if not self.available and not self.refresh():
            return None

        resolved_model = self._resolve_model(model)
        if not resolved_model:
            return None

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": resolved_model,
                    "prompt": prompt,
                    "stream": stream,
                    "temperature": temperature,
                    "top_p": top_p,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            return (data.get("response") or "").strip() or None
        except requests.RequestException as exc:
            logger.error("Ollama generation failed: %s", exc)
            return None

    def generate_stream(
        self,
        prompt: str,
        model: str = "llama3.1",
        temperature: float = 0.3,
        top_p: float = 0.9,
    ) -> Generator[str, None, None]:
        if not self.available and not self.refresh():
            yield "Ollama is not available."
            return

        resolved_model = self._resolve_model(model)
        if not resolved_model:
            yield "No Ollama model is available."
            return

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": resolved_model,
                    "prompt": prompt,
                    "stream": True,
                    "temperature": temperature,
                    "top_p": top_p,
                },
                stream=True,
                timeout=self.timeout,
            )
            response.raise_for_status()
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    chunk = requests.models.complexjson.loads(line)
                except ValueError:
                    continue
                text = chunk.get("response")
                if text:
                    yield text
        except requests.RequestException as exc:
            logger.error("Ollama streaming failed: %s", exc)
            yield f"Ollama request failed: {exc}"

    def list_models(self) -> List[str]:
        if self.available:
            self.available_models = self._fetch_models()
        return self.available_models

    def is_available(self) -> bool:
        return self.available or self.refresh()

    def health_check(self) -> Dict[str, object]:
        return {
            "available": self.is_available(),
            "url": self.base_url,
            "models": len(self.list_models()) if self.is_available() else 0,
            "model_list": self.available_models,
        }


_ollama_instance: Optional[OllamaWrapper] = None


def get_ollama() -> OllamaWrapper:
    global _ollama_instance
    if _ollama_instance is None:
        _ollama_instance = OllamaWrapper()
    return _ollama_instance


def reset_ollama() -> OllamaWrapper:
    global _ollama_instance
    _ollama_instance = OllamaWrapper()
    return _ollama_instance
