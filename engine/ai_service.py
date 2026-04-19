"""
Unified AI provider layer for local, hosted, and user-supplied models.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import requests

from engine.ollama_wrapper import get_ollama


OPENAI_COMPATIBLE_PRESETS = {
    "groq": {
        "label": "Groq (free tier with your key)",
        "base_url": "https://api.groq.com/openai/v1",
        "models": ["llama-3.3-70b-versatile", "llama3-8b-8192"],
    },
    "openrouter": {
        "label": "OpenRouter (free / paid depending on model)",
        "base_url": "https://openrouter.ai/api/v1",
        "models": ["meta-llama/llama-3.1-8b-instruct:free", "mistralai/mistral-7b-instruct:free"],
    },
}

HUGGINGFACE_MODELS = [
    "HuggingFaceH4/zephyr-7b-beta",
    "mistralai/Mistral-7B-Instruct-v0.2",
]


@dataclass
class AISettings:
    provider: str = "rule_based"
    model: str = "llama3.1"
    api_key: str = ""
    base_url: str = ""
    huggingface_model: str = HUGGINGFACE_MODELS[0]
    timeout_seconds: int = 90


def get_provider_options() -> List[Tuple[str, str]]:
    return [
        ("rule_based", "Built-in guidance only"),
        ("ollama", "Ollama (local)"),
        ("huggingface", "Hugging Face Inference"),
        ("groq", OPENAI_COMPATIBLE_PRESETS["groq"]["label"]),
        ("openrouter", OPENAI_COMPATIBLE_PRESETS["openrouter"]["label"]),
        ("custom_openai", "Custom OpenAI-compatible endpoint"),
    ]


def default_model_for_provider(provider: str) -> str:
    if provider == "ollama":
        models = get_ollama().list_models()
        return models[0] if models else "llama3.1"
    if provider in OPENAI_COMPATIBLE_PRESETS:
        return OPENAI_COMPATIBLE_PRESETS[provider]["models"][0]
    if provider == "huggingface":
        return HUGGINGFACE_MODELS[0]
    return "rule-based"


def provider_status(settings: AISettings) -> Dict[str, object]:
    provider = settings.provider
    if provider == "rule_based":
        return {
            "available": True,
            "provider": provider,
            "message": "Built-in deterministic guidance is ready.",
            "models": ["rule-based"],
        }
    if provider == "ollama":
        health = get_ollama().health_check()
        return {
            "available": bool(health["available"]),
            "provider": provider,
            "message": f"Ollama at {health['url']}" if health["available"] else "Ollama not reachable.",
            "models": health.get("model_list", []),
        }
    if provider == "huggingface":
        has_token = bool(settings.api_key)
        return {
            "available": has_token,
            "provider": provider,
            "message": "Ready to call Hugging Face Inference." if has_token else "Add a Hugging Face token to enable hosted AI.",
            "models": HUGGINGFACE_MODELS,
        }
    if provider in OPENAI_COMPATIBLE_PRESETS:
        preset = OPENAI_COMPATIBLE_PRESETS[provider]
        has_key = bool(settings.api_key)
        return {
            "available": has_key,
            "provider": provider,
            "message": f"Ready to call {preset['label']}." if has_key else f"Add an API key for {preset['label']}.",
            "models": preset["models"],
        }
    if provider == "custom_openai":
        ready = bool(settings.api_key and settings.base_url and settings.model)
        return {
            "available": ready,
            "provider": provider,
            "message": "Ready to call your custom OpenAI-compatible endpoint." if ready else "Provide base URL, model, and API key.",
            "models": [settings.model] if settings.model else [],
        }
    return {"available": False, "provider": provider, "message": "Unknown provider.", "models": []}


def available_models(settings: AISettings) -> List[str]:
    if settings.provider == "ollama":
        models = get_ollama().list_models()
        return models or ["llama3.1"]
    if settings.provider == "huggingface":
        return HUGGINGFACE_MODELS
    if settings.provider in OPENAI_COMPATIBLE_PRESETS:
        return OPENAI_COMPATIBLE_PRESETS[settings.provider]["models"]
    if settings.provider == "custom_openai":
        return [settings.model] if settings.model else []
    return ["rule-based"]


def generate_text(prompt: str, settings: AISettings, temperature: float = 0.2) -> Optional[str]:
    provider = settings.provider
    if provider == "rule_based":
        return None
    if provider == "ollama":
        return get_ollama().generate(prompt=prompt, model=settings.model, temperature=temperature)
    if provider == "huggingface":
        return _generate_huggingface(prompt, settings, temperature)
    if provider in OPENAI_COMPATIBLE_PRESETS:
        preset = OPENAI_COMPATIBLE_PRESETS[provider]
        return _generate_openai_compatible(
            prompt=prompt,
            base_url=preset["base_url"],
            api_key=settings.api_key,
            model=settings.model,
            temperature=temperature,
            timeout_seconds=settings.timeout_seconds,
        )
    if provider == "custom_openai":
        return _generate_openai_compatible(
            prompt=prompt,
            base_url=settings.base_url,
            api_key=settings.api_key,
            model=settings.model,
            temperature=temperature,
            timeout_seconds=settings.timeout_seconds,
        )
    return None


def _generate_openai_compatible(
    prompt: str,
    base_url: str,
    api_key: str,
    model: str,
    temperature: float,
    timeout_seconds: int,
) -> Optional[str]:
    if not base_url or not api_key or not model:
        return None

    endpoint = base_url.rstrip("/") + "/chat/completions"
    response = requests.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        return None
    message = choices[0].get("message", {})
    return (message.get("content") or "").strip() or None


def _generate_huggingface(prompt: str, settings: AISettings, temperature: float) -> Optional[str]:
    if not settings.api_key:
        return None

    endpoint = f"https://api-inference.huggingface.co/models/{settings.model or settings.huggingface_model}"
    response = requests.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        },
        json={
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "return_full_text": False,
                "max_new_tokens": 700,
            },
        },
        timeout=settings.timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            return (first.get("generated_text") or "").strip() or None
    if isinstance(data, dict):
        return (data.get("generated_text") or "").strip() or None
    return None
