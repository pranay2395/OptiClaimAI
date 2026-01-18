# Streamlit Cloud Deployment Guide

## Current App Status ✅

**Latest Commit:** `5b6238a` - "fix: Unified production app with all three versions features"

**Main Application:** `streamlit_app.py`

**GitHub Repository:** https://github.com/pranay2395/OptiClaimAI

---

## Deployment Steps

### Option 1: Streamlit Cloud (Recommended)

1. **Go to:** https://streamlit.io/cloud
2. **Sign in** with GitHub account
3. **Click:** "New app"
4. **Configure:**
   - Repository: `pranay2395/OptiClaimAI`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
5. **Click:** "Deploy"

The app will be live at `https://<username>-<appname>.streamlit.app`

### Option 2: Manual Deployment

1. **Install Streamlit:**
   ```bash
   pip install streamlit
   ```

2. **Run locally:**
   ```bash
   streamlit run streamlit_app.py
   ```

3. **Access:** http://localhost:8501

---

## Features Included

### Input Modes
- ✅ **CMS-1500 Form** - Complete official form with EDI generation
- ✅ **Form Mode** - Guided form entry
- ✅ **Text Mode** - Natural language parsing
- ✅ **EDI Parser** - Direct 837 file upload and analysis
- ✅ **Analytics** - Claims insights and metrics

### Technology
- X12 837P EDI Standard Compliant
- NPPES Provider Lookup (Free API)
- Optional Ollama AI Integration
- Local-only processing (no cloud dependencies)
- Streamlit Cloud Ready

---

## Environment Requirements

### Python Version
- Python 3.10+

### Key Dependencies
- `streamlit>=1.40.0`
- `pandas`
- `pydantic` (for validation)

### Optional (for full features)
- `ollama` (for AI analysis - optional)
- `requests` (for NPPES lookup)

---

## Configuration

### File: `.streamlit/config.toml`
```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
font = "sans serif"

[server]
headless = true
port = 8501
```

---

## App Architecture

```
OptiClaimAI/
├── streamlit_app.py          ← MAIN ENTRY POINT
├── streamlit_app_v2.py       ← Previous version (backup)
├── streamlit_app_v3.py       ← Strict Streamlit mode (backup)
├── model/
│   ├── cms1500_schema.py     ← CMS-1500 dataclasses
│   ├── claim_builder.py      ← Claim object construction
│   └── prompts/
├── engine/
│   ├── parser.py             ← EDI 837 parser
│   ├── validator.py          ← Claims validation
│   ├── analytics.py          ← Analytics engine
│   ├── edi_837p_generator.py ← EDI generation
│   ├── validate_cms1500.py   ← Post-submit validation
│   ├── nppes_lookup.py       ← Provider lookup
│   ├── ai_engine_factory.py  ← Optional AI
│   └── rules_engine_v2.py    ← Rules engine
├── streamlit_ui/
│   ├── cms1500_form_v3.py    ← CMS-1500 form UI
│   ├── form_input.py         ← Form mode UI
│   ├── text_input.py         ← Text mode UI
│   ├── edi_mode.py           ← EDI upload UI
│   └── results_display.py    ← Results rendering
├── data/
│   ├── sample_837/           ← Sample EDI files
│   └── parsed_json/          ← Sample JSON
├── .streamlit/
│   └── config.toml           ← Streamlit config
└── requirements.txt          ← Python dependencies
```

---

## Unified UI (v3 Production)

### Header
- Unified branding: "🏥 OptiClaimAI"
- Tagline: "Healthcare Claims Intelligence Platform"
- PHI Warning (prominent)

### Sidebar Navigation
- **Input Mode** radio selector
  - 📋 CMS-1500
  - 📝 Form
  - 📄 Text
  - 📊 EDI Parser
  - 📈 Analytics
- **About** section
- **Reset** button

### Content Areas
Each mode provides:
1. **Input** - Data collection
2. **Processing** - Validation & conversion
3. **Output** - Results display
4. **Download** - Export options (.837, .json)

---

## Testing

### Validation Tests
```bash
python test_v3_validation.py
```

### Comprehensive Tests
```bash
python test_cms1500_comprehensive.py
```

### System Check
```python
from engine.validate_cms1500 import validate_cms1500
from engine.edi_837p_generator import cms1500_to_edi837p
# Test locally
```

---

## Troubleshooting

### App Won't Load
- Check Python version: `python --version`
- Reinstall deps: `pip install -r requirements.txt`
- Clear cache: `streamlit cache clear`

### Import Errors
- Verify PYTHONPATH includes project root
- Check relative imports in modules

### Missing Features
- Ensure all files in `streamlit_ui/` exist
- Check engine modules are accessible

---

## Production Checklist

- ✅ All three versions unified into single `streamlit_app.py`
- ✅ Consistent UI across all modes
- ✅ No missing imports or broken references
- ✅ Graceful fallback for optional features
- ✅ Committed to GitHub: `5b6238a`
- ✅ Ready for Streamlit Cloud deployment
- ✅ All tests passing
- ✅ Config file optimized for cloud

---

## Support

**GitHub Issues:** https://github.com/pranay2395/OptiClaimAI/issues

**Latest Commit:** `5b6238a` (Jan 17, 2026)

**Status:** ✅ Production Ready
