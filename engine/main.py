from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from app.backend.parser import parse_837
from app.backend.model import predict_denial
import json

app = FastAPI(title='OptiClaimAI Backend')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

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

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app.backend.main:app', host='0.0.0.0', port=8000, reload=True)
