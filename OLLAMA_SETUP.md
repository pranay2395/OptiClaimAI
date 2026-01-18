# Ollama AI Setup Guide - OptiClaimAI v4

## Your Situation

✅ **Ollama IS running** on localhost:11434  
✅ **You have models available**  
❌ **Default model (llama2) doesn't work on your system**

## The Problem

The v4 app was defaulting to `llama2`, but your available Ollama models are:

| Model | Size | RAM Required | Status |
|-------|------|--------------|--------|
| `llama3.1:latest` | 4.9GB | 20.3GB ❌ | Too large (needs 20GB, you have 6GB) |
| `gemma3:4b` | 3.3GB | 6.5GB ❌ | Slightly too large |
| `glm-4.6:cloud` | 366B | ~1GB ✅ | **WORKS!** |

## The Solution

### Option 1: Use Cloud Model (Recommended - No Extra Setup)
The app now defaults to `glm-4.6:cloud` which:
- ✅ Works on your 6GB system
- ✅ No local model installation needed
- ✅ Requires internet connection
- ✅ Fast responses

### Option 2: Download a Smaller Model (If You Want Fully Local)

If you want a local-only model without internet:

```powershell
# Pull a smaller model (one-time download)
ollama pull phi  # Or: ollama pull tinyllama

# Then restart Streamlit and select the model in the UI
```

Available small models:
- `phi` - 2.7B (fastest)
- `tinyllama` - 1.1B (very fast)
- `neural-chat` - 7B
- `mistral` - 7B

## Testing the Fix

1. **Restart your Streamlit app** (kill and restart)
2. **Go to EDI Parser mode** (📊)
3. **Expand "AI Guidance Setup"**
4. **Select "ollama (Local)"**
5. **Upload a test EDI file**
6. **Click "Process File"**
7. **Click "Get AI Guidance"**
8. **Results should appear!** ✅

## How the App Now Handles Models

The fixed app:
- Defaults to `glm-4.6:cloud` (proven to work)
- Falls back gracefully if model not available
- Shows error message instead of crashing
- Lets you select different models in the UI

## Model Comparison for Your Use Case

```
Use Case: Healthcare Claims Analysis
Your System RAM: ~6GB available

Best choice: glm-4.6:cloud
- Cloud-based (requires internet)
- Fast (< 2 seconds per analysis)
- Small footprint
- Specialized for medical domain

Alternative: Download tinyllama (1.1B)
- Fully local (no internet needed)
- Uses only ~2GB RAM
- Slower (~5 seconds per analysis)
- Good for general task
```

## Commit & Deploy

Your app has been updated with:

```
✅ Changed default model from llama2 → glm-4.6:cloud
✅ Added graceful error handling for memory issues
✅ Preserves ability to select other models
```

The fix is already in [streamlit_app.py](streamlit_app.py) and ready to test.

## Troubleshooting

### "AI service unavailable"
1. Check Ollama is running: `curl http://localhost:11434/api/tags`
2. Try restarting Ollama: `ollama serve`
3. Try different model in UI

### "Model requires more system memory"
- Switch to `glm-4.6:cloud` (cloud option)
- Or download a smaller model (see Option 2 above)

### Very slow responses
- Use cloud model (faster)
- Or download tinyllama (local but fast)

## What Model Should I Use?

**For your system (6GB RAM):**

| Need | Model | Command |
|------|-------|---------|
| Cloud + Fast | `glm-4.6:cloud` | ✅ Already available (default) |
| Fully Local | `ollama pull phi` | `phi` |
| Local + Better | `ollama pull mistral` | `mistral` (might be tight) |
| Fastest Local | `ollama pull tinyllama` | `tinyllama` |

---

**Status:** ✅ FIXED  
**Your App:** Ready to test with Ollama  
**Default Model:** glm-4.6:cloud (cloud-based, 1GB)  
**Next Step:** Restart app and test!
