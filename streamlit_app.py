"""
OptiClaimAI Streamlit application.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import List

import pandas as pd
import streamlit as st

from engine.business_features import (
    build_follow_up_worklist,
    build_team_dashboard,
    generate_claim_report,
    plan_has_feature,
    pricing_tiers,
)
from engine.claim_analysis import (
    ClaimAnalysis,
    apply_autofix_and_reanalyze,
    analyze_edi_claims,
    analyze_form_claim,
    build_ai_prompt,
    build_rule_based_guidance,
    overall_summary,
    summarize_issues,
)
from engine.ollama_wrapper import get_ollama, reset_ollama
from engine.parser import EDI837Parser
from engine.product_store import append_lead, save_report
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
    if "selected_claim_index" not in st.session_state:
        st.session_state.selected_claim_index = 0
    if "selected_plan" not in st.session_state:
        st.session_state.selected_plan = "Starter"
    if "last_saved_report" not in st.session_state:
        st.session_state.last_saved_report = ""


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
    st.sidebar.title("Workspace")
    st.session_state.selected_plan = st.sidebar.selectbox(
        "Active plan",
        ["Starter", "Pro", "Enterprise"],
        help="Demo plan gating for monetizable features.",
    )

    st.sidebar.divider()
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


def refresh_selected_claim(index: int, item: ClaimAnalysis) -> None:
    st.session_state.analyses[index] = item
    st.session_state.ai_guidance = {}


def feature_locked(feature_key: str, upgrade_plan: str) -> bool:
    if plan_has_feature(st.session_state.selected_plan, feature_key):
        return False
    st.info(f"Available on the {upgrade_plan} plan and above.")
    return True


def render_paid_features(item: ClaimAnalysis, index: int) -> None:
    claim = item.claim
    validation = item.validation
    guidance = get_ai_guidance(item, st.session_state.selected_model)

    st.markdown("### Paid workflow features")
    feature_tabs = st.tabs(
        [
            "Payer pack",
            "Claim scrubber",
            "Docs checklist",
            "Appeal letter",
            "Integrations",
            "Claim follow-up",
        ]
    )

    with feature_tabs[0]:
        if not feature_locked("payer_pack", "Pro"):
            profile = validation.get("payer_profile", {})
            st.markdown(f"**Payer:** {claim.payer_name or 'Other'}")
            st.caption(profile.get("description", "No payer profile loaded."))
            required_fields = profile.get("required_fields", [])
            if required_fields:
                st.markdown("**Rules this payer tends to care about**")
                for field in required_fields:
                    st.markdown(f"- `{field}`")

    with feature_tabs[1]:
        if not feature_locked("claim_scrubber", "Starter"):
            if item.suggested_corrections:
                st.markdown("**Suggested corrections**")
                for suggestion in item.suggested_corrections:
                    st.markdown(
                        f"- **{suggestion['field']}**: {suggestion['action']} "
                        f"(current: `{suggestion['current']}`, suggested: `{suggestion['suggested']}`)"
                    )
            else:
                st.success("No quick scrubber fixes were suggested.")

            if st.button("Apply safe auto-fixes", key=f"autofix_{index}", use_container_width=True):
                updated = apply_autofix_and_reanalyze(item)
                refresh_selected_claim(index, updated)
                if updated.autofix_changes:
                    st.success("Applied safe fixes:\n" + "\n".join(f"- {change}" for change in updated.autofix_changes))
                else:
                    st.info("No safe auto-fixes were available.")
                st.rerun()

    with feature_tabs[2]:
        if not feature_locked("docs_checklist", "Pro"):
            checklist = item.documentation_checklist
            if checklist:
                for doc in checklist:
                    st.markdown(f"- **{doc['item']}** ({doc['status']}): {doc['reason']}")
            else:
                st.info("No additional documentation suggestions were generated.")

    with feature_tabs[3]:
        if not feature_locked("appeal_letter", "Starter"):
            st.text_area("Generated appeal letter", value=item.appeal_letter, height=280, key=f"appeal_{index}")
            st.download_button(
                "Download appeal letter",
                item.appeal_letter,
                file_name=f"{claim.claim_id or 'claim'}_appeal.txt",
                use_container_width=True,
            )

    with feature_tabs[4]:
        if not feature_locked("integrations", "Enterprise"):
            st.caption("Integration-ready payload for an EHR, billing platform, or webhook.")
            st.json(item.integration_payload)
            st.download_button(
                "Download integration payload",
                json.dumps(item.integration_payload, indent=2, default=str),
                file_name=f"{claim.claim_id or 'claim'}_integration_payload.json",
                mime="application/json",
                use_container_width=True,
            )

    with feature_tabs[5]:
        if not feature_locked("follow_up", "Pro"):
            existing_submission_date = validation.get("submission_date")
            if isinstance(existing_submission_date, str):
                try:
                    existing_submission_date = datetime.fromisoformat(existing_submission_date).date()
                except ValueError:
                    existing_submission_date = date.today()
            elif not isinstance(existing_submission_date, date):
                existing_submission_date = date.today()
            submission_date = st.date_input(
                "Submission date",
                value=existing_submission_date,
                key=f"submission_date_{index}",
            )
            if st.button("Update follow-up status", key=f"followup_{index}", use_container_width=True):
                item.validation["submission_date"] = submission_date.isoformat() if submission_date else None
                refresh_selected_claim(index, item)
                st.success("Follow-up status updated.")
                st.rerun()
            worklist = build_follow_up_worklist([item])
            if worklist:
                row = worklist[0]
                st.markdown(f"- **Status:** {row['status']}")
                st.markdown(f"- **Next action:** {row['next_action']}")
                st.markdown(f"- **Days since submission:** {row['days_since_submission']}")

    st.markdown("### Saved outputs")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save claim report", key=f"save_report_{index}", use_container_width=True):
            report_payload = generate_claim_report(item, guidance)
            saved_path = save_report(claim.claim_id or f"claim_{index + 1}", report_payload)
            st.session_state.last_saved_report = str(saved_path)
            st.success(f"Saved report to {saved_path}")
    with col2:
        st.download_button(
            "Download claim report JSON",
            json.dumps(generate_claim_report(item, guidance), indent=2, default=str),
            file_name=f"{claim.claim_id or 'claim'}_report.json",
            mime="application/json",
            use_container_width=True,
        )

    if st.session_state.last_saved_report:
        st.caption(f"Last saved report: {st.session_state.last_saved_report}")


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
    payer_override = st.selectbox(
        "Payer for uploaded claims",
        ["Unknown", "Medicare", "Medicaid", "Blue Cross Blue Shield", "Aetna", "Cigna", "UnitedHealthcare", "Other"],
        key="single_upload_payer",
    )
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
            if payer_override != "Unknown":
                for item in analyses:
                    item.claim.payer_name = payer_override
                    refreshed = apply_autofix_and_reanalyze(item)
                    item.validation = refreshed.validation
                    item.suggested_corrections = refreshed.suggested_corrections
                    item.documentation_checklist = refreshed.documentation_checklist
                    item.appeal_letter = refreshed.appeal_letter
                    item.integration_payload = refreshed.integration_payload
            st.session_state.analyses = analyses
            st.session_state.ai_guidance = {}
            st.success(f"Parsed and reviewed {len(analyses)} claim(s).")
        except Exception as exc:
            st.error(f"Could not process the uploaded file: {exc}")


def handle_batch_tab() -> None:
    st.subheader("Batch claim triage")
    st.caption("Upload multiple EDI files to generate a prioritized worklist for a billing team.")
    if not plan_has_feature(st.session_state.selected_plan, "batch_triage"):
        st.info("Batch triage is available on the Pro plan and above.")
        return
    payer_override = st.selectbox(
        "Payer for batch claims",
        ["Unknown", "Medicare", "Medicaid", "Blue Cross Blue Shield", "Aetna", "Cigna", "UnitedHealthcare", "Other"],
        key="batch_upload_payer_override",
    )
    uploaded_files = st.file_uploader(
        "Upload multiple .837, .edi, or .txt files",
        type=["837", "edi", "txt"],
        accept_multiple_files=True,
        key="batch_upload",
    )
    if not uploaded_files:
        return

    if st.button("Run batch triage", type="primary", use_container_width=True):
        batch_analyses: List[ClaimAnalysis] = []
        failed_files: List[str] = []
        for uploaded_file in uploaded_files:
            try:
                content = uploaded_file.read().decode("utf-8")
                parsed_data = EDI837Parser().parse(content)
                results = analyze_edi_claims(parsed_data)
                for item in results:
                    if not item.claim.claim_id:
                        item.claim.claim_id = uploaded_file.name
                    if payer_override != "Unknown":
                        item.claim.payer_name = payer_override
                        refreshed = apply_autofix_and_reanalyze(item)
                        item.validation = refreshed.validation
                        item.suggested_corrections = refreshed.suggested_corrections
                        item.documentation_checklist = refreshed.documentation_checklist
                        item.appeal_letter = refreshed.appeal_letter
                        item.integration_payload = refreshed.integration_payload
                batch_analyses.extend(results)
            except Exception:
                failed_files.append(uploaded_file.name)

        if batch_analyses:
            st.session_state.analyses = batch_analyses
            st.session_state.ai_guidance = {}
            st.session_state.selected_claim_index = 0
            st.success(f"Loaded {len(batch_analyses)} claims into the triage queue.")
        if failed_files:
            st.warning("Some files could not be processed:\n" + "\n".join(f"- {name}" for name in failed_files))


def render_team_dashboard(analyses: List[ClaimAnalysis]) -> None:
    st.markdown("## Team dashboard")
    if not plan_has_feature(st.session_state.selected_plan, "team_dashboard"):
        st.info("Team dashboard is available on the Pro plan and above.")
        return
    dashboard = build_team_dashboard(analyses)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total claim value", f"${dashboard['total_claim_value']:,.2f}")
        payer_mix = dashboard["payer_mix"]
        if payer_mix:
            st.markdown("**Payer mix**")
            st.dataframe(pd.DataFrame([{"payer": key, "claims": value} for key, value in payer_mix.items()]), use_container_width=True)
    with col2:
        risk_mix = dashboard["risk_mix"]
        if risk_mix:
            st.markdown("**Risk mix**")
            st.dataframe(pd.DataFrame([{"risk": key, "claims": value} for key, value in risk_mix.items()]), use_container_width=True)
        top_issue_fields = dashboard["top_issue_fields"]
        if top_issue_fields:
            st.markdown("**Top cleanup areas**")
            st.dataframe(
                pd.DataFrame([{"field": field, "count": count} for field, count in top_issue_fields]),
                use_container_width=True,
            )


def render_worklist(analyses: List[ClaimAnalysis]) -> None:
    st.markdown("## Follow-up worklist")
    if not plan_has_feature(st.session_state.selected_plan, "follow_up"):
        st.info("Follow-up worklists are available on the Pro plan and above.")
        return
    worklist = build_follow_up_worklist(analyses)
    if worklist:
        worklist_df = pd.DataFrame(worklist)
        st.dataframe(worklist_df, use_container_width=True)
        st.download_button(
            "Download worklist CSV",
            worklist_df.to_csv(index=False),
            file_name="follow_up_worklist.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("No worklist entries yet.")


def render_pricing_page() -> None:
    st.markdown("## Pricing and packaging")
    cols = st.columns(len(pricing_tiers()))
    for column, tier in zip(cols, pricing_tiers()):
        with column:
            st.markdown(f"### {tier['plan']}")
            st.markdown(f"**{tier['price']}**")
            st.caption(tier["best_for"])
            for feature in tier["features"]:
                st.markdown(f"- {feature}")

    st.divider()
    st.markdown("### Contact sales")
    with st.form("lead_capture_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            lead_name = st.text_input("Name *")
            lead_email = st.text_input("Email *")
        with col2:
            company_name = st.text_input("Company")
            interested_plan = st.selectbox("Interested plan", ["Starter", "Pro", "Enterprise"])
        use_case = st.text_area("What workflow do you want help with?", placeholder="Denial prevention, batch QA, payer-specific rules, integrations...")
        submitted = st.form_submit_button("Save lead", use_container_width=True)

    if submitted:
        if not lead_name.strip() or not lead_email.strip():
            st.error("Name and email are required.")
        else:
            saved = append_lead(
                {
                    "name": lead_name.strip(),
                    "email": lead_email.strip(),
                    "company": company_name.strip(),
                    "interested_plan": interested_plan,
                    "use_case": use_case.strip(),
                }
            )
            st.success(f"Lead saved to {saved}")


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

    tab_form, tab_upload, tab_batch, tab_chat, tab_pricing = st.tabs(
        ["Quick claim form", "EDI upload", "Batch triage", "AI assistant", "Pricing"]
    )

    with tab_form:
        handle_form_tab()
    with tab_upload:
        handle_upload_tab()
    with tab_batch:
        handle_batch_tab()
    with tab_chat:
        handle_chat_tab()
    with tab_pricing:
        render_pricing_page()

    if not st.session_state.analyses:
        st.info("No claim has been reviewed yet. Use the quick form or upload an EDI file to start.")
        return

    st.divider()
    render_summary(st.session_state.analyses)
    st.divider()
    render_team_dashboard(st.session_state.analyses)
    st.divider()
    render_worklist(st.session_state.analyses)
    st.divider()

    if len(st.session_state.analyses) == 1:
        render_claim_details(st.session_state.analyses[0])
        render_paid_features(st.session_state.analyses[0], 0)
        return

    labels = [claim_label(item, idx) for idx, item in enumerate(st.session_state.analyses)]
    selected_label = st.selectbox("Choose a claim to inspect", labels, index=st.session_state.selected_claim_index)
    selected_index = labels.index(selected_label)
    st.session_state.selected_claim_index = selected_index
    render_claim_details(st.session_state.analyses[selected_index])
    render_paid_features(st.session_state.analyses[selected_index], selected_index)


if __name__ == "__main__":
    main()
