"""
AI Engine Factory - Lazy loading, optional AI
No global initialization. AI is disabled if no provider/key exists.
"""

import os
from typing import Optional


class AIEngineFactory:
    """Factory for lazy-loading optional AI engines"""
    
    _instance = None
    _ai_engine = None
    _ai_enabled = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def enable_ai(cls, provider: str = None, api_key: str = None) -> bool:
        """
        Enable AI with optional provider and API key.
        
        Args:
            provider: 'ollama', 'openai', 'anthropic', or None
            api_key: Provider-specific API key
        
        Returns:
            bool: True if AI was enabled, False otherwise
        """
        try:
            if provider == 'ollama':
                from engine.ai_engine import OllamaEngine
                cls._ai_engine = OllamaEngine()
                cls._ai_enabled = True
                return True
            
            elif provider == 'openai' and api_key:
                os.environ['OPENAI_API_KEY'] = api_key
                # Lazy import to avoid early dependency
                try:
                    from engine.ai_engine import OpenAIEngine
                    cls._ai_engine = OpenAIEngine(api_key)
                    cls._ai_enabled = True
                    return True
                except:
                    cls._ai_enabled = False
                    return False
            
            cls._ai_enabled = False
            return False
        except Exception as e:
            cls._ai_enabled = False
            return False
    
    @classmethod
    def get_ai_engine(cls):
        """Get AI engine if enabled, None otherwise"""
        return cls._ai_engine if cls._ai_enabled else None
    
    @classmethod
    def is_enabled(cls) -> bool:
        """Check if AI is enabled"""
        return cls._ai_enabled
    
    @classmethod
    def disable_ai(cls):
        """Disable AI completely"""
        cls._ai_engine = None
        cls._ai_enabled = False


def get_ai_engine() -> Optional:
    """Singleton getter for AI engine"""
    return AIEngineFactory.get_ai_engine()


def is_ai_enabled() -> bool:
    """Check if AI is enabled"""
    return AIEngineFactory.is_enabled()
