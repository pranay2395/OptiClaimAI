# 🚀 STREAMLIT CLOUD DEPLOYMENT

**Status:** Ready to deploy  
**Repository:** https://github.com/pranay2395/OptiClaimAI  
**Main File:** streamlit_app_v2.py  
**Branch:** main  

---

## STEP 1: Prepare (✅ DONE)

- ✅ Code committed to GitHub
- ✅ All tests passing
- ✅ .streamlit/config.toml created
- ✅ requirements.txt updated
- ✅ README.md present

---

## STEP 2: Deploy to Streamlit Cloud

### Option A: Via Web UI (Recommended - 2 minutes)

1. Open https://share.streamlit.io/
2. Click "Create app"
3. Sign in with GitHub account
4. Select repository: `pranay2395/OptiClaimAI`
5. Set these values:
   - **Repository:** pranay2395/OptiClaimAI
   - **Branch:** main
   - **Main file path:** streamlit_app_v2.py
6. Click "Deploy"
7. Wait 2-3 minutes for deployment
8. Share the link (e.g., https://opticlaimai.streamlit.app)

### Option B: Via Streamlit CLI

```bash
streamlit run streamlit_app_v2.py --deploy --email your@email.com
```

---

## STEP 3: Post-Deployment Verification

Once deployed, verify these features work on the cloud:

**Test Form Mode:**
- Enter patient info
- Enter provider info
- Submit claim
- See validation results

**Test Text Mode:**
- Paste: "Patient John Doe, DOB 1985-05-15, visited Dr. Smith (NPI 1234567890) on 2024-01-10. Diagnosis M54.5, CPT 99213 ($150)"
- Click "Parse & Validate"
- See extracted data and validation

**Test EDI Mode:**
- Upload a .837 file
- See parsed claim results

**Check AI Status:**
- Sidebar should show: "⚠️ Ollama is unavailable - AI features disabled"
- (This is expected on cloud - Ollama runs locally only)

---

## STEP 4: Monitor & Share

Once live:

```
✅ Share the URL with users
✅ Monitor usage in Streamlit Cloud dashboard
✅ Check logs for errors
✅ Collect feedback
```

---

## CONFIGURATION

### Secrets (if adding later)

Create `.streamlit/secrets.toml` for sensitive data:

```toml
[ollama]
host = "http://localhost:11434"
model = "llama2"
timeout = 30
```

### Environment Variables

Streamlit Cloud will inherit from:
- GitHub repo environment
- Streamlit Cloud dashboard secrets

---

## TROUBLESHOOTING

**App won't start?**
- Check GitHub connection
- Verify streamlit_app_v2.py exists
- Check requirements.txt for all dependencies

**AI features unavailable on cloud?**
- Expected! Ollama runs locally, not on cloud
- App gracefully disables AI features
- Users can still validate claims deterministically

**Import errors?**
- Verify all packages in requirements.txt are listed
- Run `pip freeze > requirements.txt` locally before pushing

---

## NEXT STEPS AFTER DEPLOYMENT

1. **Week 1:** Monitor stability, collect feedback
2. **Week 2:** 
   - Add bulk CSV upload
   - Add 837 EDI generation
   - Add database persistence
3. **Week 3+:** User authentication, payer integrations

---

## QUICK REFERENCE

| Feature | Status | Works on Cloud |
|---------|--------|---|
| Form Input | ✅ Built | ✅ Yes |
| Text Input | ✅ Built | ✅ Yes |
| EDI Upload | ✅ Built | ✅ Yes |
| Validation | ✅ Built | ✅ Yes |
| AI Explanations | ✅ Built | ⚠️ Disabled (no Ollama) |
| Database | ❌ Not in MVP | N/A |
| Auth | ❌ Not in MVP | N/A |

---

**Ready to deploy!** 🚀

Last sync: `6333363` (main branch)  
All code committed ✅  
Configuration complete ✅  
Dependencies listed ✅  
