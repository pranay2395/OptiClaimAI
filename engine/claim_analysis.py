"""
Shared claim analysis helpers for Streamlit workflows.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from engine.business_features import (
    apply_safe_autofixes,
    documentation_checklist,
    generate_appeal_letter,
    get_payer_profile,
    integration_payload,
    payer_specific_issues,
    suggest_corrections,
)
from engine.rules_engine_v2 import ClaimRulesEngine
from model.claim_builder import ClaimBuilder
from model.claim_schema import Claim, Diagnosis, Patient, Procedure, Provider


def _parse_edi_date(value: Optional[str]):
    if not value:
        return None
    value = str(value).strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_claim_from_parsed_edi(claim_data: Dict) -> Claim:
    patient_data = claim_data.get("patient", {}) or {}
    provider_data = claim_data.get("provider", {}) or {}
    diagnoses = claim_data.get("diagnoses", []) or []
    service_lines = claim_data.get("service_lines", []) or []

    procedures = [
        Procedure(
            code=(line.get("procedure_code") or "").strip(),
            units=_safe_float(line.get("service_units"), 1.0),
            charge=_safe_float(line.get("line_item_charge"), 0.0),
        )
        for line in service_lines
        if (line.get("procedure_code") or "").strip()
    ]

    return Claim(
        patient=Patient(
            first_name=(patient_data.get("name_first") or "").strip(),
            last_name=(patient_data.get("name_last") or "").strip(),
            date_of_birth=_parse_edi_date(patient_data.get("dob")),
            gender=patient_data.get("gender"),
            insurance_id=patient_data.get("id_number"),
        ),
        provider=Provider(
            first_name=(provider_data.get("name_first") or "").strip(),
            last_name=(provider_data.get("name_last") or "").strip(),
            npi=(provider_data.get("id_number") or "").strip(),
        ),
        diagnoses=[
            Diagnosis(code=(diag.get("code") or "").strip(), primary=(idx == 0))
            for idx, diag in enumerate(diagnoses)
            if (diag.get("code") or "").strip()
        ],
        procedures=procedures,
        service_date=_parse_edi_date(claim_data.get("service_date")),
        claim_amount=_safe_float(claim_data.get("claim_amount"), 0.0),
        claim_id=claim_data.get("claim_id"),
        place_of_service=claim_data.get("place_of_service"),
    )


@dataclass
class ClaimAnalysis:
    claim: Claim
    validation: Dict
    source_label: str
    parsed_claim: Optional[Dict] = None
    suggested_corrections: List[Dict] = field(default_factory=list)
    documentation_checklist: List[Dict] = field(default_factory=list)
    appeal_letter: str = ""
    integration_payload: Dict = field(default_factory=dict)
    autofix_changes: List[str] = field(default_factory=list)


def _enrich_validation(claim: Claim, validation: Dict, authorization_ready: bool = False) -> Dict:
    enriched = dict(validation)
    enriched["authorization_ready"] = authorization_ready
    enriched["payer_profile"] = get_payer_profile(claim.payer_name)
    payer_issues = payer_specific_issues(claim, enriched)
    if payer_issues:
        issues = list(enriched.get("issues", [])) + payer_issues
        enriched["issues"] = issues
        enriched["issue_count"] = len(issues)
        enriched["high_count"] = enriched.get("high_count", 0) + len(payer_issues)
        enriched["denial_risk_score"] = min(enriched.get("denial_risk_score", 0) + (10 * len(payer_issues)), 100)
        score = enriched["denial_risk_score"]
        if score >= 70:
            enriched["denial_risk_level"] = "VERY HIGH"
        elif score >= 50:
            enriched["denial_risk_level"] = "HIGH"
        elif score >= 30:
            enriched["denial_risk_level"] = "MEDIUM"
        else:
            enriched["denial_risk_level"] = "LOW"
        enriched["is_valid"] = not any("CRITICAL" in issue.get("severity", "") for issue in issues)
    return enriched


def _build_analysis(claim: Claim, validation: Dict, source_label: str, parsed_claim: Optional[Dict] = None) -> ClaimAnalysis:
    corrections = suggest_corrections(claim, validation)
    checklist = documentation_checklist(claim, validation)
    appeal = generate_appeal_letter(claim, validation)
    payload = integration_payload(claim, validation)
    return ClaimAnalysis(
        claim=claim,
        validation=validation,
        source_label=source_label,
        parsed_claim=parsed_claim,
        suggested_corrections=corrections,
        documentation_checklist=checklist,
        appeal_letter=appeal,
        integration_payload=payload,
    )


def analyze_form_claim(form_data: Dict) -> ClaimAnalysis:
    claim = ClaimBuilder.from_form(form_data)
    validation = ClaimRulesEngine().validate(claim)
    validation = _enrich_validation(claim, validation, authorization_ready=bool(form_data.get("has_prior_auth")))
    return _build_analysis(claim, validation, "Quick claim form", form_data)


def analyze_edi_claims(parsed_data: Dict) -> List[ClaimAnalysis]:
    analyses: List[ClaimAnalysis] = []
    for idx, parsed_claim in enumerate(parsed_data.get("claims", []), start=1):
        claim = build_claim_from_parsed_edi(parsed_claim)
        if not claim.claim_id:
            claim.claim_id = f"Claim {idx}"
        validation = ClaimRulesEngine().validate(claim)
        validation = _enrich_validation(claim, validation, authorization_ready=False)
        analyses.append(_build_analysis(claim, validation, "EDI 837 upload", parsed_claim))
    return analyses


def apply_autofix_and_reanalyze(item: ClaimAnalysis) -> ClaimAnalysis:
    claim = item.claim
    changes = apply_safe_autofixes(claim)
    validation = ClaimRulesEngine().validate(claim)
    validation = _enrich_validation(claim, validation, authorization_ready=item.validation.get("authorization_ready", False))
    refreshed = _build_analysis(claim, validation, item.source_label, item.parsed_claim)
    refreshed.autofix_changes = changes
    return refreshed


def summarize_issues(issues: List[Dict]) -> Dict[str, List[Dict]]:
    grouped: Dict[str, List[Dict]] = {
        "CRITICAL": [],
        "HIGH": [],
        "MEDIUM": [],
        "LOW": [],
        "INFO": [],
    }
    for issue in issues:
        severity = (issue.get("severity") or "INFO").split()[-1]
        grouped.setdefault(severity, []).append(issue)
    return grouped


def build_rule_based_guidance(claim: Claim, validation: Dict) -> str:
    issues = validation.get("issues", [])
    grouped = summarize_issues(issues)
    critical_or_high = grouped["CRITICAL"] + grouped["HIGH"]
    probable_reasons = critical_or_high[:3] or issues[:3]

    top_fields = Counter(issue.get("field") or "claim" for issue in issues)
    focus_areas = ", ".join(field for field, _ in top_fields.most_common(3)) or "claim details"

    reasons_lines = "\n".join(
        f"- {issue['message']}" for issue in probable_reasons
    ) or "- No major denial triggers were detected."

    fix_lines = []
    for issue in probable_reasons:
        field = issue.get("field") or "claim"
        if field == "patient":
            fix_lines.append("- Complete the patient demographics and insurance/member details before resubmission.")
        elif field == "provider":
            fix_lines.append("- Correct the provider identity details, especially the NPI and name fields.")
        elif field == "diagnoses":
            fix_lines.append("- Add or correct the ICD-10 diagnosis codes and make sure they match the visit.")
        elif field == "procedures":
            fix_lines.append("- Review CPT/HCPCS procedure codes, units, and charge amounts for each service line.")
        else:
            fix_lines.append("- Review the missing claim header details and align them with the source documentation.")

    if not fix_lines:
        fix_lines.append("- Review the claim once more and submit when you are comfortable with the data.")

    unique_fix_lines = []
    for line in fix_lines:
        if line not in unique_fix_lines:
            unique_fix_lines.append(line)

    readiness = "Ready to submit." if validation.get("is_valid") else "Not ready to submit yet."

    return (
        "### Submission Readiness\n"
        f"**{readiness}** Denial risk is **{validation.get('denial_risk_level', 'UNKNOWN')}** "
        f"({validation.get('denial_risk_score', 0)}%).\n\n"
        "### Probable Denial Reasons\n"
        f"{reasons_lines}\n\n"
        "### How To Improve Acceptance Odds\n"
        f"{chr(10).join(unique_fix_lines)}\n\n"
        "### Billing Team Focus\n"
        f"Concentrate on **{focus_areas}** first. Once the critical items are resolved, revalidate before submission."
    )


def build_ai_prompt(claim: Claim, validation: Dict) -> str:
    issue_lines = "\n".join(
        f"- [{issue.get('severity', 'INFO')}] {issue.get('message', '')}"
        for issue in validation.get("issues", [])
    ) or "- No issues detected."

    diagnosis_codes = ", ".join(diag.code for diag in claim.diagnoses) or "None"
    procedure_codes = ", ".join(proc.code for proc in claim.procedures) or "None"

    return f"""You are a senior healthcare claims denial-prevention specialist.

Write a concise markdown response for a medical biller reviewing a claim before submission.
Do not return JSON.
Use these sections exactly:
## Submission Readiness
## Probable Denial Reasons
## How To Improve Acceptance Odds
## Billing Team Focus

Claim snapshot:
- Claim ID: {claim.claim_id or 'Not provided'}
- Patient: {claim.patient.first_name} {claim.patient.last_name}
- Provider: {claim.provider.first_name} {claim.provider.last_name}
- Service date: {claim.service_date or 'Not provided'}
- Claim amount: ${claim.claim_amount:,.2f}
- Diagnosis codes: {diagnosis_codes}
- Procedure codes: {procedure_codes}
- Denial risk: {validation.get('denial_risk_level', 'UNKNOWN')} ({validation.get('denial_risk_score', 0)}%)

Validation issues:
{issue_lines}

Explain the most likely denial causes in plain English and give practical corrections that improve acceptance odds."""


def overall_summary(analyses: List[ClaimAnalysis]) -> Dict[str, int]:
    total_claims = len(analyses)
    valid_claims = sum(1 for item in analyses if item.validation.get("is_valid"))
    total_issues = sum(item.validation.get("issue_count", 0) for item in analyses)
    high_risk = sum(
        1
        for item in analyses
        if item.validation.get("denial_risk_level") in {"VERY HIGH", "HIGH"}
    )
    return {
        "total_claims": total_claims,
        "valid_claims": valid_claims,
        "total_issues": total_issues,
        "high_risk_claims": high_risk,
    }
