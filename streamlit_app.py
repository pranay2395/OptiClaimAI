"""
OptiClaimAI Streamlit application.
"""

from __future__ import annotations

import json
from typing import List

import streamlit as st

from engine.claim_analysis import (
    ClaimAnalysis,
    analyze_edi_claims,
    analyze_form_claim,
    build_ai_prompt,
    build_rule_based_guidance,
    overall_summary,
    summarize_issues,
)
from engine.ollama_wrapper import get_ollama, reset_ollama
from engine.parser import EDI837Parser
from streamlit_ui.cms1500_form_v3 import render_cms1500_form


st.set_page_config(
    page_title="OptiClaimAI",
    page_icon=":hospital:",
    layout="wide",
)


def init_session() -> None:
    if "analyses" not in st.session_state:
        st.session_state.analyses = []
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = "llama3.1"
    if "ai_guidance" not in st.session_state:
        st.session_state.ai_guidance = {}


def claim_label(item: ClaimAnalysis, index: int) -> str:
    claim_id = item.claim.claim_id or f"Claim {index + 1}"
    patient = f"{item.claim.patient.first_name} {item.claim.patient.last_name}".strip()
    if not patient:
        patient = "Unknown patient"
    return f"{claim_id} - {patient}"


def get_ai_guidance(item: ClaimAnalysis, model: str) -> str:
    cache_key = f"{item.claim.claim_id or id(item.claim)}::{model}"
    if cache_key in st.session_state.ai_guidance:
        return st.session_state.ai_guidance[cache_key]

    fallback = build_rule_based_guidance(item.claim, item.validation)
    ollama = get_ollama()
    if not ollama.is_available():
        st.session_state.ai_guidance[cache_key] = fallback
        return fallback

    prompt = build_ai_prompt(item.claim, item.validation)
    response = ollama.generate(prompt=prompt, model=model, temperature=0.2)
    guidance = response or fallback
    st.session_state.ai_guidance[cache_key] = guidance
    return guidance


def render_sidebar() -> None:
    st.sidebar.title("AI Settings")
    if st.sidebar.button("Refresh Ollama connection", use_container_width=True):
        reset_ollama()

    ollama = get_ollama()
    status = ollama.health_check()

    if status["available"]:
        st.sidebar.success(f"Ollama connected at {status['url']}")
        models = status["model_list"] or ["llama3.1"]
        default_index = models.index(st.session_state.selected_model) if st.session_state.selected_model in models else 0
        st.session_state.selected_model = st.sidebar.selectbox(
            "Model",
            models,
            index=default_index,
            help="Used for claim coaching after validation.",
        )
    else:
        st.sidebar.warning("Ollama is not available. The app will fall back to built-in guidance.")
        st.sidebar.code("ollama serve")
        st.sidebar.caption("If you have no model installed yet, run `ollama pull llama3.1`.")

    st.sidebar.divider()
    st.sidebar.caption(
        "This app now shows human-readable claim guidance first. Structured JSON is available only in expandable debug sections."
    )


def render_summary(analyses: List[ClaimAnalysis]) -> None:
    summary = overall_summary(analyses)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Claims reviewed", summary["total_claims"])
    with col2:
        st.metric("Valid now", summary["valid_claims"])
    with col3:
        st.metric("Total issues", summary["total_issues"])
    with col4:
        st.metric("High-risk claims", summary["high_risk_claims"])


def render_claim_details(item: ClaimAnalysis) -> None:
    validation = item.validation
    claim = item.claim

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Denial risk", validation.get("denial_risk_level", "UNKNOWN"))
    with col2:
        st.metric("Risk score", f"{validation.get('denial_risk_score', 0)}%")
    with col3:
        st.metric("Ready to submit", "Yes" if validation.get("is_valid") else "No")

    st.markdown("### Claim snapshot")
    st.markdown(
        "\n".join(
            [
                f"- **Patient:** {f'{claim.patient.first_name} {claim.patient.last_name}'.strip() or 'Unknown'}",
                f"- **Provider:** {f'{claim.provider.first_name} {claim.provider.last_name}'.strip() or 'Unknown'}",
                f"- **Service date:** {str(claim.service_date) if claim.service_date else 'Not provided'}",
                f"- **Diagnosis codes:** {', '.join(diag.code for diag in claim.diagnoses) or 'None'}",
                f"- **Procedure codes:** {', '.join(proc.code for proc in claim.procedures) or 'None'}",
                f"- **Claim amount:** ${claim.claim_amount:,.2f}",
            ]
        )
    )

    st.markdown("### Submission coaching")
    with st.spinner("Preparing guidance..."):
        st.markdown(get_ai_guidance(item, st.session_state.selected_model))

    grouped = summarize_issues(validation.get("issues", []))
    st.markdown("### Validation issues")
    if validation.get("issue_count", 0) == 0:
        st.success("No blocking issues were found.")
    else:
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
            issues = grouped.get(severity, [])
            if not issues:
                continue
            with st.expander(f"{severity} ({len(issues)})", expanded=severity in {"CRITICAL", "HIGH"}):
                for issue in issues:
                    field = issue.get("field") or "claim"
                    st.markdown(f"- **{field}**: {issue.get('message', 'Unknown issue')}")

    with st.expander("Technical details"):
        st.json(
            json.loads(
                json.dumps(
                    {
                "validation": validation,
                "parsed_claim": item.parsed_claim,
                "claim": claim.to_dict(),
                    },
                    default=str,
                )
            )
        )


def handle_form_tab() -> None:
    form_data = render_cms1500_form()
    if form_data:
        st.session_state.analyses = [analyze_form_claim(form_data)]
        st.session_state.ai_guidance = {}
        st.success("Claim validated. Review the guidance below.")


def handle_upload_tab() -> None:
    st.subheader("EDI 837 Upload")
    uploaded_file = st.file_uploader("Upload a .837, .edi, or .txt claim file", type=["837", "edi", "txt"])
    if not uploaded_file:
        return

    if st.button("Validate uploaded claim", type="primary", use_container_width=True):
        try:
            content = uploaded_file.read().decode("utf-8")
            parsed_data = EDI837Parser().parse(content)
            analyses = analyze_edi_claims(parsed_data)
            if not analyses:
                st.error("No claims were parsed from the file.")
                return
            st.session_state.analyses = analyses
            st.session_state.ai_guidance = {}
            st.success(f"Parsed and reviewed {len(analyses)} claim(s).")
        except Exception as exc:
            st.error(f"Could not process the uploaded file: {exc}")


def handle_chat_tab() -> None:
    st.subheader("Ask about claims")
    st.caption("Use this for general billing questions or to ask follow-up questions about the current review.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask a claim, denial, or billing question")
    if not prompt:
        return

    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    ollama = get_ollama()
    current_context = ""
    if st.session_state.analyses:
        latest = st.session_state.analyses[0]
        current_context = json.dumps(
            {
                "claim_id": latest.claim.claim_id,
                "risk": latest.validation.get("denial_risk_level"),
                "issues": latest.validation.get("issues", []),
            },
            default=str,
        )

    if ollama.is_available():
        system_prompt = (
            "You are a practical healthcare claims assistant. Answer in short markdown. "
            "Use the current claim context when it is relevant. Avoid JSON unless explicitly asked.\n\n"
            f"Current claim context: {current_context or 'None'}"
        )
        response = ollama.generate(
            prompt=f"{system_prompt}\n\nUser: {prompt}\nAssistant:",
            model=st.session_state.selected_model,
            temperature=0.3,
        )
        answer = response or "I could not get a response from Ollama. Check that the model is installed."
    else:
        answer = (
            "Ollama is not connected right now, so chat is limited. Start it with `ollama serve` and install a model "
            "such as `ollama pull llama3.1` to enable AI responses."
        )

    st.session_state.chat_history.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.markdown(answer)


def main() -> None:
    init_session()
    render_sidebar()

    st.title("OptiClaimAI")
    st.write("Validate claims, understand likely denial reasons, and get practical next-step guidance before submission.")

    tab_form, tab_upload, tab_chat = st.tabs(["Quick claim form", "EDI upload", "AI assistant"])

    with tab_form:
        handle_form_tab()
    with tab_upload:
        handle_upload_tab()
    with tab_chat:
        handle_chat_tab()

    if not st.session_state.analyses:
        st.info("No claim has been reviewed yet. Use the quick form or upload an EDI file to start.")
        return

    st.divider()
    render_summary(st.session_state.analyses)
    st.divider()

    if len(st.session_state.analyses) == 1:
        render_claim_details(st.session_state.analyses[0])
        return

    labels = [claim_label(item, idx) for idx, item in enumerate(st.session_state.analyses)]
    selected_label = st.selectbox("Choose a claim to inspect", labels)
    selected_index = labels.index(selected_label)
    render_claim_details(st.session_state.analyses[selected_index])


if __name__ == "__main__":
    main()
