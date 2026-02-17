from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.backend.parser import parse_837
from engine.model import predict_denial
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title='OptiClaimAI Backend')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

class PromptRequest(BaseModel):
    prompt: str

@app.get('/health')
def health():
    return {'status':'ok'}

@app.post('/parse')
async def parse(file: UploadFile = File(...)):
    content = await file.read()
    raw = content.decode('utf-8', errors='ignore')
    parsed = parse_837(raw)
    return parsed

@app.post('/predict')
async def predict(file: UploadFile = File(...), use_ollama: bool = True):
    content = await file.read()
    raw = content.decode('utf-8', errors='ignore')
    parsed = parse_837(raw)
    result = predict_denial(raw, parsed, use_ollama=use_ollama)
    return result

@app.get('/health')
def health_detailed():
    return {
        'status': 'ok',
        'ai_provider': os.getenv('AI_PROVIDER', 'ollama'),
        'ollama_url': os.getenv('OLLAMA_URL', 'http://localhost:8000')
    }

@app.post('/analyze')
async def analyze(request: PromptRequest):
    """
    Analyze a claim based on the provided prompt
    """
    try:
        import requests
        
        # Try to use configured AI service
        ai_provider = os.getenv('AI_PROVIDER', 'ollama')
        ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:8000')
        ollama_model = os.getenv('OLLAMA_MODEL', 'llama2')
        
        if ai_provider == 'ollama':
            ollama_response = requests.post(
                f"{ollama_url}/api/generate",
                json={"model": ollama_model, "prompt": request.prompt, "stream": False},
                timeout=30
            )
            if ollama_response.status_code == 200:
                result = ollama_response.json().get('response', '')
                return {"response": result, "status": "success", "provider": "ollama"}
        
        # Fallback response
        response = f"Analysis: {request.prompt[:100]}... [Processed by OptiClaimAI Backend]"
        return {
            "response": response,
            "status": "success",
            "provider": "fallback"
        }
    except Exception as e:
        return {
            "response": f"Error: {str(e)}",
            "status": "error",
            "provider": "error"
        }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app.backend.main:app', host='0.0.0.0', port=8000, reload=True)
