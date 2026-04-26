## Engine Layer

The engine is intentionally compact and focused on the current product path.

### Main modules

- `parser.py`: reads uploaded 837 content
- `claim_analysis.py`: canonical analysis pipeline
- `rules_engine_v2.py`: deterministic validation rules
- `business_features.py`: payer packs, pricing, exports, automation payloads
- `ai_service.py`: provider-agnostic AI integration
- `product_store.py`: saved reports and lead capture
- `ollama_wrapper.py`: local Ollama helper

### Design goal

Keep one production path only. Older duplicate analytics, validation, and response-formatting helpers were removed to reduce maintenance cost.
