# OptiClaimAI

AI-powered pre-submission claims validation tool for 837 files.

## Features

- Parse and validate 837 EDI files
- AI-driven denial prediction using rules or Ollama
- In-memory processing for security (no file storage)
- PHI masking in results
- Streamlit web UI

## Setup

1. Clone the repo
2. Install dependencies: `pip install -r requirements.txt`
3. Run the app: `streamlit run streamlit_app.py`

## Usage

Upload a synthetic 837 file or use included samples. Toggle Ollama for local AI inference.

## Disclaimer

This is a demo tool. Do not upload real PHI. Files are processed in-session only.

## Deployment

Deploy to Streamlit Cloud by pushing to GitHub.

