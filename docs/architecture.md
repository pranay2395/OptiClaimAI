# OptiClaimAI Architecture

## Current Shape

The project is a single Streamlit product, not a split UI/backend service.

### Primary flow

1. User completes office or DME intake in `streamlit_ui/cms1500_form_v3.py`
2. The app converts the intake into the canonical claim model in `model/claim_builder.py`
3. `engine/claim_analysis.py` runs deterministic validation and enriches the result with:
   - payer-specific issues
   - documentation checklist
   - auto-fix suggestions
   - appeal letter
   - integration payload
4. `streamlit_app.py` presents:
   - denial prevention guidance
   - saved reports
   - batch triage
   - follow-up queue
   - pricing / lead capture
   - premium automation webhook sending

## AI Layer

`engine/ai_service.py` supports:

- built-in deterministic fallback
- Ollama
- Hugging Face Inference
- Groq
- OpenRouter
- custom OpenAI-compatible endpoints

If AI is unavailable, the app still works with deterministic guidance.

## Persistence

`engine/secure_store.py` stores runtime artifacts in `runtime_data/`:

- encrypted PHI-bearing reports
- business-contact sales leads
- lightweight audit trail

The local runtime store follows a safer development posture:

- minimum necessary persistence
- encryption at rest for claim artifacts
- short retention window with automatic cleanup
- no raw PHI written to the audit file

## Product Philosophy

The codebase is intentionally compact:

- one main app
- one intake form
- one analysis pipeline
- one business-features layer

Duplicate legacy UI paths and unused helper modules were removed to keep the maintenance surface small.
