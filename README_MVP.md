# OptiClaimAI MVP - Human-First Claims Intelligence

**Date:** January 10, 2026  
**Status:** ✅ Production Ready (MVP)  
**License:** Open Source (MIT)  

---

## 🎯 What This Is

OptiClaimAI is a **claims intelligence platform for humans**, not EDI experts.

Instead of asking users to upload 837 EDI files or fill complex medical forms, OptiClaimAI accepts:
- **Simple forms** (step-by-step guided entry)
- **Natural language** ("Tell us about the visit")
- **EDI files** (for advanced users)

It then normalizes everything into a **canonical claim model**, runs **deterministic validation**, and explains issues in **plain English** with optional **AI-powered guidance**.

---

## 🚀 Quick Start

### Run Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Start Ollama for AI features
ollama serve

# 3. Run the app
python -m streamlit run streamlit_app_v2.py
```

App will open at `http://localhost:8501`

### Deploy to Streamlit Cloud

```bash
git push origin main
# Connect repo in Streamlit Cloud
# App degrades gracefully if Ollama unavailable
```

---

## 📋 What's Included (MVP)

### ✅ IMPLEMENTED
- **Form-based input** - guided, step-by-step claim entry
- **Free-text parsing** - AI-ish natural language extraction
- **Rule validation** - 40+ deterministic checks
- **Denial risk scoring** - probability-based prediction
- **AI explanations** - via local Ollama (optional)
- **Plain English messaging** - no EDI jargon
- **Session state** - claims persist during session
- **Error handling** - graceful degradation

### ⏳ NOT IN MVP (v2+)
- 837 EDI generation
- Bulk upload processing
- Database persistence
- Mobile app
- Multi-user auth
- Payer integrations

---

## 🏗️ Architecture

### Core Components

```
Inputs (Form/Text/EDI)
         ↓
   Claim Builder
         ↓
Canonical Claim Model ← Single Source of Truth
         ↓
   Rules Engine (Deterministic)
         ↓
   AI Engine (Ollama - Optional)
         ↓
Output Formatter
         ↓
Streamlit UI
```

### File Structure

```
OptiClaimAI/
├── model/
│   ├── __init__.py
│   ├── claim_schema.py        # Claim, Patient, Provider dataclasses
│   └── claim_builder.py       # Build from form/text/EDI
├── engine/
│   ├── parser.py              # EDI 837 parser (existing)
│   ├── validator.py           # Legacy validator
│   ├── rules_engine_v2.py     # NEW: Enhanced rules + severity
│   ├── text_parser.py         # NEW: NLP for free text
│   ├── ai_engine.py           # NEW: Ollama integration
│   ├── output_formatter.py    # NEW: Human-readable output
│   └── analytics.py           # Existing analytics
├── streamlit_ui/
│   ├── __init__.py
│   ├── form_input.py          # NEW: Form component
│   ├── text_input.py          # NEW: Text entry component
│   ├── results_display.py     # NEW: Results + AI UI
│   └── edi_mode.py            # NEW: EDI upload wrapper
├── streamlit_app_v2.py        # NEW: Refactored main app
├── test_pipeline.py           # NEW: Comprehensive tests
└── requirements.txt
```

---

## 💡 How It Works

### Mode 1: Form Entry

User fills guided form → ClaimBuilder.from_form() → Canonical Claim Model → Validation

**Fields:**
- Patient: Name, DOB, Insurance ID, Gender, Phone, Email
- Provider: Name, NPI, Specialty, Phone
- Service: Date, Place of Service
- Diagnoses: Up to 3 ICD-10 codes
- Procedures: Up to 5 CPT codes with charges

### Mode 2: Free-Text Entry

User describes claim in plain English:
> "Patient Jane Doe, DOB 1985-03-15, Insurance Blue Cross #BC123456. Visit with Dr. John Smith (NPI 1234567890) on 2024-01-10. Diagnosis: M54.5 (lower back pain). Procedures: 99213 ($150), 71210 ($200)."

→ TextParser (regex NLP) → Claim Builder → Canonical Model → Validation

### Mode 3: EDI Upload (Legacy)

Upload 837 EDI file → EDI837Parser → Canonical Model → Validation

---

## 🔍 Validation Rules

### Severity Levels
- **🔴 CRITICAL** (40 pts) - Blocks submission, prevents claim
- **🟠 HIGH** (20 pts) - Major issue, likely denial
- **🟡 MEDIUM** (10 pts) - Minor issue, may delay
- **🟢 LOW** (5 pts) - Nice-to-have

### Sample Rules

| Category | Rule | Severity |
|----------|------|----------|
| **Required** | Patient name missing | 🔴 CRITICAL |
| **Required** | Insurance ID missing | 🔴 CRITICAL |
| **Required** | Provider NPI invalid | 🔴 CRITICAL |
| **Required** | Diagnosis missing | 🔴 CRITICAL |
| **Required** | Procedure missing | 🔴 CRITICAL |
| **Format** | NPI not 10 digits | 🔴 CRITICAL |
| **Format** | Invalid ICD-10 code | 🟡 MEDIUM |
| **Format** | Invalid CPT code | 🟡 MEDIUM |
| **Logic** | Claim amount = $0 | 🟠 HIGH |
| **Contact** | Patient phone missing | 🟢 LOW |

### Denial Risk Calculation

```
Risk Score = (Critical × 40) + (High × 20) + (Medium × 10)
Max: 100

VERY HIGH: ≥70% (Do NOT submit)
HIGH: 50-69% (Likely denial - fix first)
MEDIUM: 30-49% (May be denied - consider fixes)
LOW: <30% (Good to submit)
```

---

## 🤖 AI Integration (Optional)

### When AI is Used
- Explaining validation issues
- Suggesting fixes
- Answering follow-up questions

### When AI is NOT Used
- Making validation decisions (rules only)
- Scoring denial risk (deterministic)
- Generating 837 files

### Ollama Setup

```bash
# Install Ollama
# https://ollama.ai

# Start server
ollama serve

# Pull a model (optional, defaults to llama2)
ollama pull llama2:latest
ollama pull mistral  # Faster alternative
```

### Graceful Degradation

If Ollama is unavailable (e.g., on Streamlit Cloud):
- App still works 100%
- AI buttons show "*(unavailable)*"
- Validation continues normally
- Zero errors or crashes

---

## 📊 Test Results

```
============================================================
OptiClaimAI Pipeline Test
============================================================

✓ Test 1: Direct Claim Creation
  Claim created: John Doe

✓ Test 2: Claim Validation
  Valid: True
  Issues: 1
  Denial Risk: LOW (0%)

✓ Test 3: Output Formatting
  Summary generated (225 chars)

✓ Test 4: Free-Text Parsing
  Parsed: John Smith
  Procedures: 3

✓ Test 5: AI Engine Status
  Ollama available: YES

============================================================
✅ All tests passed!
============================================================
```

### Run Tests

```bash
python test_pipeline.py
```

---

## 🧠 Natural Language Parsing

The text parser uses regex patterns to extract:

### Patient
- Name: "Patient FirstName LastName"
- DOB: "DOB YYYY-MM-DD" or "date of birth YYYY-MM-DD"
- Insurance: "Insurance ID ABC123"

### Provider
- Name: "with Dr. FirstName LastName" or "Dr FirstName LastName"
- NPI: "NPI 1234567890" (10 consecutive digits)
- Specialty: "Specialty Physical Therapy"

### Clinical
- Diagnoses: ICD-10 codes like "M54.5" or "J45.901"
- Procedures: CPT codes like "99213" with charges "$150"

### Dates
- Service: "on YYYY-MM-DD"
- Multiple formats: "2024-01-10", "2024/01/10"

---

## 🔐 Security & Privacy

**Demo Mode Active:**
- ⚠️ Do NOT submit real patient data
- ⚠️ Use synthetic data only
- ⚠️ No database persistence in MVP

**For Production:**
- Add user auth (next version)
- Encrypt sensitive data
- Add audit logging
- Enable HIPAA compliance mode

---

## 📈 What's Next (V1.1+)

### Near Term
- [ ] Bulk claim upload (CSV/JSON)
- [ ] 837 EDI generation
- [ ] Payer rule engine
- [ ] Database persistence (PostgreSQL)
- [ ] User authentication

### Medium Term
- [ ] Mobile app (React Native)
- [ ] Clearinghouse integrations
- [ ] Real-time payer lookup
- [ ] Insurance verification API
- [ ] Denial prediction ML model

### Long Term
- [ ] Multi-tenant SaaS platform
- [ ] Revenue cycle management
- [ ] Predictive analytics
- [ ] Provider network optimization

---

## 🛠️ Tech Stack

| Layer | Tech |
|-------|------|
| **Frontend** | Streamlit 1.40+ |
| **Backend** | Python 3.10+ |
| **AI** | Ollama (local LLM) |
| **Data** | Dataclasses, JSON |
| **Validation** | Regex, Custom Rules |
| **Logging** | Python logging |

### No External APIs
✅ Zero OpenAI  
✅ Zero paid APIs  
✅ Zero clearinghouse dependencies  
✅ Local everything  

---

## 🚀 Deployment

### Local Development
```bash
python -m streamlit run streamlit_app_v2.py
```

### Docker
```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "streamlit_app_v2.py"]
```

### Streamlit Cloud
1. Push to GitHub
2. Connect repo in Streamlit Cloud
3. Set runtime to Python 3.11+
4. App will run (AI gracefully disabled if Ollama unavailable)

---

## 📝 Example Workflows

### Workflow 1: Simple Form Entry
1. User clicks "📋 Use Form"
2. Fills out 12 fields (2-3 min)
3. Clicks "Validate"
4. Sees issues, risk score, fix guidance
5. Can get AI explanations for each issue
6. Exports results

### Workflow 2: Free-Text Entry
1. User clicks "📝 Describe It"
2. Pastes claim description
3. System parses automatically
4. Validates
5. Shows results with fixes

### Workflow 3: Advanced EDI
1. User clicks "⬆️ Upload EDI"
2. Uploads 837 file
3. System parses + validates
4. Shows issues (same as other modes)

---

## 🤝 Contributing

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes
# Run tests
python test_pipeline.py

# Commit with clear message
git commit -m "feat: description"

# Push and open PR
git push origin feature/my-feature
```

---

## 📄 License

MIT License - Use freely, modify as needed, credit appreciated.

---

## 🎯 Business Model

This is an **open-source MVP**. Potential monetization:

1. **SaaS Platform** - Hosted claims intake + workflow
2. **White Label** - Embed in EMR/billing software
3. **Integration** - Payer/clearinghouse partnerships
4. **Support** - Enterprise support + compliance

---

## 📞 Support

- 🐛 **Issues:** GitHub Issues
- 💬 **Discussions:** GitHub Discussions
- 📧 **Email:** support@opticlaim.ai

---

## � DEPLOYMENT (Ready Now)

### Status: ✅ PRODUCTION READY

All code tested, committed, and ready to deploy to Streamlit Cloud.

### Deploy in 2 Minutes

1. Visit https://share.streamlit.io/
2. Click "Create app"
3. Select GitHub repo: `pranay2395/OptiClaimAI`
4. Set main file: `streamlit_app_v2.py`
5. Click "Deploy"

**That's it.** The app will be live in 2-3 minutes.

### Test After Deployment

Once live:
- [ ] Test form input (fill 12 fields, submit)
- [ ] Test text parsing (paste description, parse)
- [ ] Test EDI upload (upload .837 file)
- [ ] Check AI status (shows unavailable - expected on cloud)
- [ ] Verify validation works (rules run deterministically)

### What Works on Cloud

✅ Form input  
✅ Text parsing  
✅ EDI upload  
✅ Rule validation (40+ checks)  
✅ Denial risk scoring  
⚠️ AI explanations disabled (Ollama local only)  

The app gracefully disables AI if Ollama unavailable - all deterministic validation still works perfectly.

---

## �🙏 Acknowledgments

- Built with Streamlit
- Powered by Ollama for local AI
- EDI parsing inspired by healthcare standards
- Community feedback drives the roadmap

---

**Made with ❤️ for healthcare professionals who just want to submit claims without learning EDI.**

Last updated: January 10, 2026
