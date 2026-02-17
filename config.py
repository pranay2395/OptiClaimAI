"""
OptiClaimAI Configuration Management
Handles environment variables with fallbacks and validation
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration management with validation"""
    
    # AI Provider Settings
    AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama").lower()
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:8000")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "30"))
    
    # Fallback Providers
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    # Backend Service
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")
    BACKEND_TIMEOUT = int(os.getenv("BACKEND_TIMEOUT", "30"))
    
    # Application
    APP_NAME = os.getenv("APP_NAME", "OptiClaimAI")
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    
    @staticmethod
    def get_ai_config():
        """Get AI configuration with validation"""
        return {
            "provider": Config.AI_PROVIDER,
            "ollama_url": Config.OLLAMA_URL,
            "ollama_model": Config.OLLAMA_MODEL,
            "ollama_timeout": Config.OLLAMA_TIMEOUT,
            "backend_url": Config.BACKEND_URL,
            "backend_timeout": Config.BACKEND_TIMEOUT,
            "openai_key": Config.OPENAI_API_KEY,
        }
    
    @staticmethod
    def validate_ai_service():
        """Validate AI service is accessible"""
        import requests
        
        if Config.AI_PROVIDER == "ollama":
            try:
                response = requests.get(
                    f"{Config.OLLAMA_URL}/api/tags",
                    timeout=Config.OLLAMA_TIMEOUT
                )
                return response.status_code == 200
            except Exception as e:
                if Config.DEBUG:
                    print(f"Ollama health check failed: {e}")
                return False
        
        return True
