"""
Chat Interface Component for Streamlit
Maintains conversation history, model selection, and AI configuration
"""

import streamlit as st
import json
from datetime import datetime
from typing import List, Dict, Optional
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.ollama_wrapper import get_ollama


# ============= SYSTEM PROMPTS (App-Aware) =============

SYSTEM_PROMPTS = {
    "healthcare_expert": {
        "name": "🏥 Healthcare Claims Expert",
        "description": "Expert assistant for healthcare claims and EDI processing",
        "prompt": """You are an expert healthcare billing and EDI claims specialist with deep knowledge of:
- X12 837P EDI standard
- CMS-1500 form requirements
- HIPAA compliance
- Claims validation and processing
- Medical coding (CPT, ICD-10, HCPCS)
- Payer rules and rejection reasons

The user is using OptiClaimAI, a healthcare claims intelligence platform. Help them:
1. Understand how to use the application
2. Fix validation errors
3. Optimize claims for faster reimbursement
4. Learn EDI standards

Keep explanations practical, not academic. Use simple language."""
    },
    
    "technical_guide": {
        "name": "🛠️ Technical Guide",
        "description": "Help understanding the app features and workflow",
        "prompt": """You are a technical guide for OptiClaimAI. Help users understand:
1. The five input modes:
   - CMS-1500 Form: Traditional paper form (140-field form)
   - Form Mode: Guided step-by-step entry
   - Text Mode: Natural language claim description
   - EDI Parser: Upload and analyze 837P files
   - Analytics: Claims insights and metrics

2. Key features:
   - X12 837P EDI generation
   - NPPES provider lookup
   - Claim validation with detailed errors
   - AI-powered claim analysis
   - Export to .837 and .json formats

3. The workflow:
   - Input your claim data
   - System validates against X12 rules
   - Fix any errors/warnings
   - Generate EDI output
   - Download or submit

Be helpful, clear, and practical."""
    },
    
    "debugging_assistant": {
        "name": "🐛 Debugging Assistant",
        "description": "Help troubleshoot app issues and errors",
        "prompt": """You are a debugging assistant for OptiClaimAI. Help users:
1. Understand error messages
2. Troubleshoot validation failures
3. Fix EDI format issues
4. Resolve provider lookup problems
5. Optimize claim submission

When users report issues:
- Ask clarifying questions
- Suggest step-by-step fixes
- Explain what went wrong
- Provide actionable solutions

Be technical but accessible."""
    },
    
    "general_chat": {
        "name": "💬 General Assistant",
        "description": "General questions about healthcare claims",
        "prompt": """You are a helpful assistant for OptiClaimAI. You can:
1. Answer questions about healthcare claims
2. Explain EDI and X12 standards
3. Help with OptiClaimAI usage
4. Provide healthcare billing guidance

Be friendly, clear, and helpful."""
    }
}


def init_chat_state():
    """Initialize chat session state"""
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'chat_model' not in st.session_state:
        st.session_state.chat_model = "llama3.1"
    if 'chat_system_prompt' not in st.session_state:
        st.session_state.chat_system_prompt = SYSTEM_PROMPTS["technical_guide"]["prompt"]
    if 'chat_system_name' not in st.session_state:
        st.session_state.chat_system_name = "technical_guide"
    if 'use_api_key' not in st.session_state:
        st.session_state.use_api_key = False
    if 'api_provider' not in st.session_state:
        st.session_state.api_provider = "ollama"
    if 'openai_key' not in st.session_state:
        st.session_state.openai_key = ""


def get_available_models() -> List[str]:
    """Get list of available models"""
    ollama = get_ollama()
    if ollama.is_available():
        models = ollama.list_models()
        if models:
            return sorted(models)
    return ["llama3.1", "glm-4", "phi"]  # Fallback suggestions


def build_context_prompt(user_message: str, app_context: Optional[str] = None) -> str:
    """Build prompt with app context"""
    context = f"""Current OptiClaimAI Context:
- Platform: Healthcare Claims Intelligence
- Features: CMS-1500 forms, EDI 837P, validation, analytics
- Input Modes: Form, Text, EDI Parser, Analytics
- Standards: X12 837P, CMS-1500
- Optional: NPPES lookup, AI-powered analysis

{app_context if app_context else ""}

User Question: {user_message}"""
    return context


def send_message(user_message: str):
    """Send message to AI and get response"""
    if not user_message.strip():
        return
    
    # Add user message to history
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_message,
        "timestamp": datetime.now().isoformat()
    })
    
    # Get response based on provider
    try:
        if st.session_state.api_provider == "ollama":
            ai_response = _get_ollama_response(user_message)
        elif st.session_state.api_provider == "openai" and st.session_state.openai_key:
            ai_response = _get_openai_response(user_message)
        else:
            ai_response = "❌ No AI provider configured. Please select a provider in settings."
        
        # Add AI response to history
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": ai_response,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": error_msg,
            "timestamp": datetime.now().isoformat()
        })


def _get_ollama_response(user_message: str) -> str:
    """Get response from Ollama"""
    ollama = get_ollama()
    
    if not ollama.is_available():
        return "❌ Ollama is not available. Make sure to run `ollama serve` first."
    
    # Build full prompt with system prompt and history
    full_prompt = f"{st.session_state.chat_system_prompt}\n\n"
    
    # Add conversation history for context
    for msg in st.session_state.chat_history[-4:]:  # Last 4 messages for context
        role = "User" if msg["role"] == "user" else "Assistant"
        full_prompt += f"{role}: {msg['content']}\n\n"
    
    full_prompt += f"User: {user_message}\n\nAssistant:"
    
    # Get response
    response = ollama.generate(
        prompt=full_prompt,
        model=st.session_state.chat_model,
        temperature=0.7,
        top_p=0.9
    )
    
    if response:
        return response
    else:
        return f"❌ No response from {st.session_state.chat_model} model. Check if model is installed."


def _get_openai_response(user_message: str) -> str:
    """Get response from OpenAI"""
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=st.session_state.openai_key)
        
        messages = [
            {"role": "system", "content": st.session_state.chat_system_prompt}
        ]
        
        # Add conversation history
        for msg in st.session_state.chat_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        messages.append({"role": "user", "content": user_message})
        
        response = client.chat.completions.create(
            model=st.session_state.chat_model or "gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"❌ OpenAI error: {str(e)}"


def render_chat_interface():
    """Main chat interface rendering function"""
    init_chat_state()
    
    st.title("💬 Chat with OptiClaimAI Assistant")
    
    # Sidebar configuration
    with st.sidebar:
        st.subheader("⚙️ Chat Settings")
        
        # AI Provider selection
        provider = st.radio(
            "AI Provider",
            ["ollama", "openai"],
            key="provider_radio"
        )
        st.session_state.api_provider = provider
        
        if provider == "ollama":
            st.info("ℹ️ Using local Ollama models (offline)")
            
            # Check Ollama status
            ollama = get_ollama()
            status = ollama.health_check()
            
            if status["available"]:
                st.success(f"✅ Connected to Ollama")
                st.caption(f"📦 {status['models']} models available")
                
                # Model selection
                available_models = status['model_list']
                if available_models:
                    model = st.selectbox(
                        "Select Model",
                        available_models,
                        index=0,
                        key="model_select"
                    )
                    st.session_state.chat_model = model
                else:
                    st.warning("❌ No Ollama models found. Run `ollama pull llama3.1`")
            else:
                st.error("❌ Ollama not running at localhost:11434")
                st.code("ollama serve", language="bash")
        
        elif provider == "openai":
            st.info("ℹ️ Using OpenAI API (online)")
            api_key = st.text_input(
                "OpenAI API Key",
                type="password",
                key="openai_key_input"
            )
            if api_key:
                st.session_state.openai_key = api_key
                st.success("✅ API Key configured")
            
            # Model selection for OpenAI
            model = st.selectbox(
                "OpenAI Model",
                ["gpt-4", "gpt-3.5-turbo"],
                key="openai_model_select"
            )
            st.session_state.chat_model = model
        
        st.divider()
        
        # System prompt selection
        st.subheader("🎯 Assistant Mode")
        selected_mode = st.selectbox(
            "Choose Assistant",
            list(SYSTEM_PROMPTS.keys()),
            format_func=lambda x: SYSTEM_PROMPTS[x]["name"],
            key="mode_select"
        )
        st.session_state.chat_system_name = selected_mode
        st.session_state.chat_system_prompt = SYSTEM_PROMPTS[selected_mode]["prompt"]
        
        st.caption(SYSTEM_PROMPTS[selected_mode]["description"])
        
        st.divider()
        
        # Clear history button
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
    
    # Main chat area
    st.divider()
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(message["content"])
            else:
                with st.chat_message("assistant"):
                    st.write(message["content"])
    
    # Input area at bottom
    st.divider()
    
    # User input
    user_input = st.chat_input(
        placeholder="Ask me anything about OptiClaimAI...",
        key="chat_input"
    )
    
    if user_input:
        send_message(user_input)
        st.rerun()
    
    # Help section
    if len(st.session_state.chat_history) == 0:
        st.info("""
        **💡 Tips:**
        - Ask about how to use OptiClaimAI
        - Ask for help with validation errors
        - Ask for healthcare billing guidance
        - Ask about EDI and X12 standards
        
        **🛠️ Available Features:**
        - CMS-1500 Form with EDI generation
        - Form mode for guided entry
        - Natural language text input
        - EDI 837P file upload and analysis
        - Claims analytics and insights
        """)


if __name__ == "__main__":
    render_chat_interface()
