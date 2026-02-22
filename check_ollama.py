#!/usr/bin/env python
"""Check Ollama status and models"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from engine.ollama_wrapper import get_ollama

def main():
    print("🔍 Checking Ollama connection...")
    ollama = get_ollama()
    
    health = ollama.health_check()
    print(f"\n✅ Connection Status:")
    print(f"   Available: {health['available']}")
    print(f"   URL: {health['url']}")
    print(f"   Models Count: {health['models']}")
    
    if health['models'] > 0:
        print(f"\n📦 Available Models:")
        for model in health['model_list']:
            print(f"   - {model}")
    else:
        print(f"\n❌ No models found!")
        print(f"   Run: ollama pull llama3.1")
        print(f"   Or: ollama pull glm-4")
        print(f"   Or: ollama pull phi")
    
    print(f"\n💡 To use chat:")
    print(f"   1. Run 'ollama serve' in another terminal")
    print(f"   2. Select 'Chat' mode in the app")
    print(f"   3. Choose a model and start chatting!")

if __name__ == "__main__":
    main()
