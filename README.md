# OptiClaimAI

OptiClaimAI is a lightweight claim-intake and denial-prevention product for small practices, billers, and DME suppliers.

## What It Does

- Captures patient intake for office and DME workflows
- Parses uploaded 837 files
- Scores denial risk before submission
- Explains probable denial reasons in plain language
- Generates intake packages, appeal drafts, and integration payloads
- Supports optional premium automation via user-provided webhook / API endpoint
- Works with:
  - built-in deterministic guidance
  - Ollama
  - Hugging Face Inference
  - Groq
  - OpenRouter
  - custom OpenAI-compatible endpoints

## Product Shape

This repo is optimized for a low-cost product tier in the `$1-$5` range by focusing on:

- simple intake
- useful pre-submit QA
- downloadable office-ready payloads
- optional automation for premium tiers

## Main App

Run the Streamlit app:

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Copy `.env.example` to `.env` and set `OPTICLAIM_MASTER_KEY` for persistent encrypted PHI report storage.

## Core Files

- `streamlit_app.py`: main product UI
- `streamlit_ui/cms1500_form_v3.py`: office and DME intake form
- `engine/claim_analysis.py`: analysis pipeline
- `engine/business_features.py`: payer packs, appeal drafts, pricing, exports
- `engine/ai_service.py`: provider-agnostic AI integration
- `engine/secure_store.py`: encrypted PHI-bearing runtime storage and lead capture

## Runtime Output

Saved product artifacts are written to:

- `runtime_data/secure_reports/`
- `runtime_data/leads.jsonl`

Claim reports are encrypted at rest. Configure `OPTICLAIM_MASTER_KEY` for a stable encryption key; otherwise the app uses an ephemeral dev-only key for the current process.

## Selling Position

The most sellable low-ticket offer in this repo is:

- Starter `$1/mo`: 5 EDI tool runs/day, 837 validation, 835 denial analysis, JSON conversion
- Pro `$3/mo`: unlimited runs, batch triage, payer packs, docs checklist, dashboard
- Enterprise `$5/mo`: integrations and automation handoff

This is positioned as a lightweight workflow tool for:

- small clinics
- DME suppliers
- independent billers
- analysts and developers debugging EDI

## Status

This is now a compact single-app Streamlit product. Older duplicate UI flows and legacy helpers were removed to reduce maintenance overhead.
