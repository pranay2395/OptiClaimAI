# OptiClaimAI v5 - Redesigned UI & Deployment Guide

## 🎯 What Changed

### Previous Version (v4)
- ❌ Left sidebar navigation
- ❌ Chat buried in menu
- ❌ Raw JSON responses
- ❌ No AI-powered analytics
- ❌ Not user-friendly

### New Version (v5) 
- ✅ **Google-style search interface** - Centered, modern design
- ✅ **AI chat as primary interaction** - Prominent search bar
- ✅ **AI-processed responses** - Human-readable insights not JSON
- ✅ **Dynamic analytics** - AI-generated explanations with visualizations
- ✅ **Smart knowledge base integration** - Uses rules + code_sets
- ✅ **Smooth transitions** - Professional UI/UX

---

## 🚀 Quick Start

### 1. Ensure Ollama is Running
```bash
# In another terminal, start Ollama
ollama serve
```

Verify Ollama is working:
```bash
python check_ollama.py
```

Expected output:
```
[OK] Connection Status:
   Available: True
   URL: http://localhost:11434
   Models Count: 3
```

### 2. Launch OptiClaimAI v5
```bash
# From workspace directory
python -m streamlit run streamlit_app_v5.py --server.port=8502
```

The app will start on **http://localhost:8502**

### 3. Use the Interface

#### Search/Home Page (Default)
- Shows OptiClaimAI branding
- Model selector (llama3.1, glm-4.6, gemma3)
- Main search bar with query input
- Three primary actions:
  - **🔍 Process** - Parse and validate claims
  - **📤 Upload File** - Upload EDI/forms
  - **💬 Chat** - Direct AI chat mode

#### Top Navigation
- **OptiClaimAI** - Return to home
- **📊 Analytics** - View analysis results
- **📋 Forms** - CMS-1500 form entry
- **☰ Menu** - Toggle sidebar history

#### Processing Flow

**For EDI Files:**
```
Upload EDI → Parser reads 837P format 
→ Validator checks all rules 
→ AI analyzes results 
→ Shows insights + visualizations
```

**For CMS-1500 Forms:**
```
Fill form → Submit 
→ Convert to EDI 
→ Validate 
→ Generate insights
```

**For Direct Chat:**
```
Ask question → AI searches knowledge base 
→ Uses rules/code_sets context 
→ Returns specific recommendations
```

---

## 🔧 Architecture

### Core Files

**Main App:**
- `streamlit_app_v5.py` - New Google-style UI (740 lines)
  - Top navigation bar
  - Centered search interface
  - Smart page routing
  - Session state management
  - Custom CSS styling

**AI & Processing:**
- `engine/response_processor.py` - Convert JSON → Human-readable insights
  - `KnowledgeLoader` - Loads CPT, ICD-10, HCPCS codes
  - `ResponseProcessor` - Processes validation results
  
- `engine/enhanced_analytics.py` - AI-powered analytics
  - `EnhancedAnalytics` class
  - Generates visualizations
  - Creates recommendations
  - Exports reports (JSON/CSV/Markdown)

- `engine/ollama_wrapper.py` - Local LLM integration (working)
  - REST API to Ollama on port 11434
  - Model listing
  - Prompt generation

**Existing Support:**
- `engine/validator.py` - Claim validation rules
- `engine/parser.py` - EDI 837P parsing
- `model/claim_schema.py` - Data structures
- `streamlit_ui/cms1500_form_v3.py` - CMS-1500 form rendering

### Knowledge Base
```
engine/code_sets/
├── cpt.csv              # Procedure codes
├── icd10.csv            # Diagnosis codes
├── hcpcs_level2.csv     # Healthcare codes
├── modifiers.csv        # Claim modifiers
├── taxonomy.csv         # Provider taxonomy
└── revenue_codes.csv    # Revenue classifications

engine/rules/
└── dhcs_rules_comprehensive.json    # Validation rules
```

---

## 📋 Features

### 1. EDI Parser Mode
- Upload 837P files
- Real-time parsing
- Validation checking
- AI analysis of claims
- Risk assessment
- Export results

### 2. CMS-1500 Form Mode
- Interactive form filling
- Field validation
- Auto-conversion to EDI
- Claim generation

### 3. Chat Mode
- Direct conversation with AI
- Access to medical knowledge
- Code lookups
- Compliance questions
- Claims explanations

### 4. Analytics Dashboard
- Summary statistics
- Error breakdown (pie/bar charts)
- Risk assessment matrix
- Top issues by frequency
- AI-powered recommendations
- Export reports (JSON/CSV/Markdown)

### 5. Smart AI Insights
- Why claims rejected
- How to fix issues
- Compliance notes
- Code explanations
- Prioritized recommendations

---

## 🎨 UI Design Details

### Layout Structure
```
┌─────────────────────────────────────────┐
│  🏥 OptiClaimAI  [📊 Analytics] [📋 Forms] [☰ Menu] │
├─────────────────────────────────────────┤
│                                         │
│  ╔═══════════════════════════════════╗  │
│  ║      OptiClaimAI                  ║  │
│  ║  Healthcare Claims Intelligence   ║  │
│  ║                                   ║  │
│  ║  Model: [✓ llama3.1] [glm-4.6]   ║  │
│  ║         [gemma3]                  ║  │
│  ║                                   ║  │
│  ║  Search or ask about claims...   ║  │
│  ║  ┌───────────────────────────────┐ ║  │
│  ║  │ [🔍 Process] [📤 Upload] [💬 Chat] │ ║  │
│  ║  └───────────────────────────────┘ ║  │
│  ╚═══════════════════════════════════╝  │
│                                         │
└─────────────────────────────────────────┘
```

### Colors & Styling
- Primary: Blue (`#1f77b4`) - Google-inspired
- Background: White/Light Gray (`#f9f9f9`)
- Text: Dark (`#202124`)
- Borders: Light gray (`#dadce0`)
- Hover: Slight shadow, color change

### Interactions
- All buttons have 0.2s transitions
- Results fade in smoothly
- Status indicators (spinners, success badges)
- Expandable/collapsible sections

---

## 🔌 API Integration

### Ollama Connection
```python
from engine.ollama_wrapper import get_ollama

ollama = get_ollama()

# Check availability
if ollama.is_available():
    # List models
    models = ollama.list_models()
    
    # Generate response
    response = ollama.generate(
        prompt="Explain this claim error",
        model="llama3.1",
        temperature=0.7
    )
```

### Response Processing
```python
from engine.response_processor import ResponseProcessor

processor = ResponseProcessor()

# Convert validation results to insights
insights = processor.process_validation_results(
    validation_results,
    parsed_claims
)

# Get AI-friendly prompts
context = insights['ai_prompt_context']
```

### Analytics
```python
from engine.enhanced_analytics import EnhancedAnalytics

analytics = EnhancedAnalytics()

# Comprehensive analysis
analysis = analytics.analyze_claims(
    validation_results,
    parsed_claims
)

# Export options
json_report = analytics.export_report(analysis, format_type='json')
md_report = analytics.export_report(analysis, format_type='markdown')
csv_report = analytics.export_report(analysis, format_type='csv')
```

---

## 📊 Response Processing Pipeline

```
Raw EDI File
├── Parser reads 837P format
├── Creates structured claim objects
│
Raw Validation Results
├── ResponseProcessor extracts errors/warnings
├── KnowledgeLoader looks up code descriptions
├── Categorizes issues by type
├── Assesses rejection risk
│
Enhanced Insights
├── AI model receives context + rules
├── Ollama generates explanations
├── Creates visualizations
├── Formats recommendations
│
User-Friendly Output
├── Summary statistics
├── AI analysis narrative
├── Step-by-step fixes
├── Charts and visualizations
├── Export options (JSON/CSV/Markdown)
```

---

## 🚢 Deployment

### Local Deployment ✅
```bash
# 1. Start Ollama
ollama serve

# 2. In another terminal, start app
python -m streamlit run streamlit_app_v5.py --server.port=8502

# 3. Open browser
# Navigate to http://localhost:8502
```

### Streamlit Cloud Deployment (Coming Soon)
```bash
# Prerequisites:
# 1. Create Streamlit account at streamlit.io
# 2. Connect GitHub repository

# Deploy:
streamlit deployment
```

**Note:** Cloud deployment requires Ollama to be accessible from internet or local LLM alternative.

### Docker Deployment (Coming Soon)
```dockerfile
FROM python:3.13
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "streamlit", "run", "streamlit_app_v5.py"]
```

---

## 🔐 Security & Compliance

### Data Privacy
- All processing happens locally
- No data sent to external services (only to local Ollama)
- Claims data never stored
- Session-based processing

### HIPAA Compliance
- PII handling: Names/DOBs treated securely
- NPI validation through NPPES
- X12 837P compliance enforced
- Audit trail available for exports

### Best Practices
- Use secure connections (HTTPS) for cloud deployment
- Authenticate access via Streamlit authentication
- Enable CORS only for trusted origins
- Regularly update code_sets and rules

---

## 🐛 Troubleshooting

### Issue: "Port 8501 is already in use"
**Solution:**
```bash
# Kill existing Streamlit process
taskkill /F /IM python.exe  # Windows

# Or use different port
python -m streamlit run streamlit_app_v5.py --server.port=8503
```

### Issue: "AI Offline | Models: 0"
**Solution:**
```bash
# Ensure Ollama is running
ollama serve

# Or pull models manually
ollama pull llama3.1
ollama pull glm-4.6
ollama pull gemma3
```

### Issue: "Could not process file"
**Checklist:**
- ✅ File is valid EDI 837P format
- ✅ File encoding is UTF-8
- ✅ Claims data valid
- ✅ Check parser logs

### Issue: Slow responses
**Optimization:**
- Close other Ollama processes
- Reduce model context size
- Use faster model (gemma3 < glm-4.6 < llama3.1)
- Limit batch size

---

## 📚 File Reference

### Session State Variables
- `current_page` - Active page (search/processing/chat/analytics)
- `chat_history` - Conversation messages
- `selected_model` - Active Ollama model
- `search_query` - Current search input
- `results` - Processed results data
- `sidebar_open` - Sidebar visibility toggle

### Response Format
```json
{
  "summary": {
    "total_claims": 100,
    "valid_claims": 85,
    "error_rate_percent": 15,
    "total_errors": 20,
    "total_warnings": 35
  },
  "error_analysis": {
    "total_unique_error_types": 5,
    "error_frequency": {...},
    "top_errors": [["missing_npi", 12], ["invalid_date", 8]]
  },
  "ai_insights": {
    "full_analysis": "...",
    "source": "AI Analysis (Ollama)",
    "confidence": "High"
  },
  "visualizations": {...},
  "recommendations": [...]
}
```

---

## 💡 Tips & Tricks

### Optimize AI Responses
- Ask specific questions: "Why is claim CLM001 rejected?"
- Provide context: "I have 50 claims with NPI errors"
- Use follow-ups: "How do I fix this?"

### Bulk Processing
- Upload EDI files with multiple claims
- System processes all claims
- Export results as CSV for your records

### Knowledge Base Update
- Add new code_sets to `engine/code_sets/`
- Update rules in `engine/rules/`
- Restart app to reload knowledge

### Custom Models
- Add new Ollama models: `ollama pull <model_name>`
- Model appears in UI selector automatically
- Use specialized models for specific tasks

---

## 📞 Support

**Problem?** Check:
1. `check_ollama.py` - Verify AI connection
2. Streamlit logs in terminal
3. Browser console (F12) for JS errors
4. This guide's Troubleshooting section

**Coming Soon:**
- Admin dashboard
- Audit logging
- Batch processing UI
- Custom model training
- API endpoints

---

**Version:** 5.0 (Redesigned UI)  
**Last Updated:** 2026-02-21  
**Status:** Production Ready ✅
