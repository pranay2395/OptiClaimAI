# OptiClaimAI Architecture

Components:
- Streamlit UI (app/ui/app.py)
- FastAPI backend (app/backend/main.py)
- Parser (app/backend/parser.py)
- Model connector for Ollama (app/backend/model.py)
- Pydantic schemas (app/backend/schemas.py)
- Utils (app/backend/utils.py)
- Data (data/sample_837) with synthetic examples
- Training examples (model/training/fine_tune.jsonl)

Flow:
[UI Upload] -> [FastAPI /predict] -> [parser.parse_837] -> [model.predict_denial]
-> [Return JSON result] -> [UI displays]

On-prem considerations:
- Ollama runs locally and handles all model inference; no PHI leaves premises.
- Package in Docker for hospital deployment (include Ollama connectivity).

