"""
Monetizable product features built on top of claim analysis.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Dict, List, Optional

from model.claim_schema import Claim


PAYER_RULES: Dict[str, Dict[str, object]] = {
    "Medicare": {
        "description": "Stricter identity, documentation, and medical-necessity expectations.",
        "required_fields": ["patient.date_of_birth", "provider.npi", "place_of_service"],
        "recommended_documents": ["Physician order", "Progress note", "Medical necessity support"],
        "authorization_required": False,
    },
    "Medicaid": {
        "description": "Often sensitive to eligibility details, rendering/billing provider alignment, and auths.",
        "required_fields": ["patient.insurance_id", "provider.npi", "place_of_service"],
        "recommended_documents": ["Eligibility verification", "Referral if required", "Progress note"],
        "authorization_required": True,
    },
    "Blue Cross Blue Shield": {
        "description": "Commercial payer rules often focus on prior auth, code pairing, and diagnosis support.",
        "required_fields": ["patient.insurance_id", "provider.npi", "place_of_service"],
        "recommended_documents": ["Benefits check", "Prior auth confirmation", "Clinical note"],
        "authorization_required": True,
    },
    "Aetna": {
        "description": "Commercial plans often need accurate authorization and coding support.",
        "required_fields": ["patient.insurance_id", "provider.npi", "place_of_service"],
        "recommended_documents": ["Benefits check", "Prior auth confirmation", "Procedure note"],
        "authorization_required": True,
    },
    "Cigna": {
        "description": "Prefers consistent member IDs, coding accuracy, and documentation for medical necessity.",
        "required_fields": ["patient.insurance_id", "provider.npi", "place_of_service"],
        "recommended_documents": ["Eligibility check", "Clinical note", "Referral if applicable"],
        "authorization_required": True,
    },
    "UnitedHealthcare": {
        "description": "Frequently sensitive to claim scrubber issues, auths, and provider identifiers.",
        "required_fields": ["patient.insurance_id", "provider.npi", "place_of_service"],
        "recommended_documents": ["Benefits check", "Prior auth confirmation", "Clinical note"],
        "authorization_required": True,
    },
    "Other": {
        "description": "Generic commercial payer workflow.",
        "required_fields": ["patient.insurance_id", "provider.npi"],
        "recommended_documents": ["Eligibility check", "Clinical note"],
        "authorization_required": False,
    },
}


def get_payer_profile(payer_name: Optional[str]) -> Dict[str, object]:
    return PAYER_RULES.get((payer_name or "Other").strip(), PAYER_RULES["Other"])


def _get_field_value(claim: Claim, path: str):
    current = claim
    for part in path.split("."):
        current = getattr(current, part, None)
        if current is None:
            return None
    return current


def payer_specific_issues(claim: Claim, validation: Dict) -> List[Dict]:
    profile = get_payer_profile(claim.payer_name)
    issues: List[Dict] = []

    for path in profile.get("required_fields", []):
        if not _get_field_value(claim, path):
            field_name = path.replace(".", "_")
            issues.append(
                {
                    "severity": "🟠 HIGH",
                    "code": "PAYER_REQUIRED_FIELD",
                    "message": f"{claim.payer_name or 'This payer'} commonly requires `{path}` to be complete before submission.",
                    "field": field_name,
                }
            )

    if profile.get("authorization_required") and not validation.get("authorization_ready"):
        issues.append(
            {
                "severity": "🟠 HIGH",
                "code": "PRIOR_AUTH_RECOMMENDED",
                "message": f"{claim.payer_name or 'This payer'} commonly expects prior authorization or referral confirmation for review-sensitive services.",
                "field": "authorization",
            }
        )

    return issues


def documentation_checklist(claim: Claim, validation: Dict) -> List[Dict]:
    profile = get_payer_profile(claim.payer_name)
    issue_fields = {issue.get("field") for issue in validation.get("issues", [])}
    checklist = []

    for item in profile.get("recommended_documents", []):
        reason = "Recommended by payer profile."
        if "diagnoses" in issue_fields or "procedures" in issue_fields:
            reason = "Helpful because coding or medical-necessity issues were detected."
        checklist.append({"item": item, "status": "Recommended", "reason": reason})

    if validation.get("denial_risk_score", 0) >= 50:
        checklist.append(
            {
                "item": "Internal pre-bill QA review",
                "status": "Strongly recommended",
                "reason": "High denial risk claims should be scrubbed before submission.",
            }
        )
    return checklist


def suggest_corrections(claim: Claim, validation: Dict) -> List[Dict]:
    suggestions: List[Dict] = []

    if claim.provider.npi and (not claim.provider.npi.isdigit() or len(claim.provider.npi) != 10):
        cleaned = "".join(ch for ch in claim.provider.npi if ch.isdigit())[:10]
        suggestions.append(
            {
                "field": "provider.npi",
                "current": claim.provider.npi,
                "suggested": cleaned or "10-digit NPI required",
                "action": "Normalize NPI to 10 digits",
                "auto_fixable": bool(cleaned and len(cleaned) == 10),
            }
        )

    if not claim.place_of_service:
        suggestions.append(
            {
                "field": "claim.place_of_service",
                "current": None,
                "suggested": "11",
                "action": "Default place of service to office",
                "auto_fixable": True,
            }
        )

    for index, diagnosis in enumerate(claim.diagnoses, start=1):
        normalized = diagnosis.code.upper().replace(" ", "")
        if normalized != diagnosis.code:
            suggestions.append(
                {
                    "field": f"diagnoses[{index}]",
                    "current": diagnosis.code,
                    "suggested": normalized,
                    "action": "Normalize diagnosis code format",
                    "auto_fixable": True,
                }
            )

    for index, procedure in enumerate(claim.procedures, start=1):
        normalized = procedure.code.upper().replace(" ", "")
        if normalized != procedure.code:
            suggestions.append(
                {
                    "field": f"procedures[{index}]",
                    "current": procedure.code,
                    "suggested": normalized,
                    "action": "Normalize procedure code format",
                    "auto_fixable": True,
                }
            )
        if procedure.charge <= 0:
            suggestions.append(
                {
                    "field": f"procedures[{index}].charge",
                    "current": procedure.charge,
                    "suggested": "Review source charge",
                    "action": "A non-zero charge is needed for submission",
                    "auto_fixable": False,
                }
            )

    return suggestions


def apply_safe_autofixes(claim: Claim) -> List[str]:
    changes: List[str] = []

    if claim.provider.npi:
        cleaned = "".join(ch for ch in claim.provider.npi if ch.isdigit())[:10]
        if cleaned and cleaned != claim.provider.npi and len(cleaned) == 10:
            claim.provider.npi = cleaned
            changes.append("Normalized provider NPI to 10 digits.")

    if not claim.place_of_service:
        claim.place_of_service = "11"
        changes.append("Filled missing place of service with 11 (office).")

    for diagnosis in claim.diagnoses:
        normalized = diagnosis.code.upper().replace(" ", "")
        if diagnosis.code != normalized:
            diagnosis.code = normalized
            changes.append(f"Normalized diagnosis code to {normalized}.")

    for procedure in claim.procedures:
        normalized = procedure.code.upper().replace(" ", "")
        if procedure.code != normalized:
            procedure.code = normalized
            changes.append(f"Normalized procedure code to {normalized}.")

    return changes


def generate_appeal_letter(claim: Claim, validation: Dict) -> str:
    issue_messages = [issue.get("message", "Claim issue identified") for issue in validation.get("issues", [])[:5]]
    payer = claim.payer_name or "the payer"
    patient = f"{claim.patient.first_name} {claim.patient.last_name}".strip() or "the patient"
    claim_id = claim.claim_id or "unassigned"

    rationale = "\n".join(f"- {message}" for message in issue_messages) or "- Please review the enclosed documentation."
    return f"""Re: Claim Appeal for Claim ID {claim_id}

To Whom It May Concern,

I am writing to request reconsideration of the above claim for {patient}. We reviewed the claim internally and identified the following items that may have contributed to a denial or pending rejection:

{rationale}

We have corrected all available claim details and recommend review of the attached supporting documentation, including the clinical note and any payer-required authorization or eligibility evidence. Based on the billed services and supporting diagnosis information, we believe this claim meets medical-necessity and billing requirements for {payer}.

Please reprocess the claim and contact our billing team if further documentation is needed.

Sincerely,
OptiClaimAI Billing Review Team
"""


def build_follow_up_worklist(analyses: List[object]) -> List[Dict]:
    today = date.today()
    worklist: List[Dict] = []
    for item in analyses:
        claim = item.claim
        validation = item.validation
        submission_date = validation.get("submission_date")
        if isinstance(submission_date, str):
            try:
                submission_date = datetime.fromisoformat(submission_date).date()
            except ValueError:
                submission_date = None
        age = (today - submission_date).days if submission_date else 0

        if not submission_date:
            next_action = "Finish corrections and submit"
            status = "Needs submission"
        elif age >= 30:
            next_action = "Call payer and request status / reprocessing update"
            status = "Aging > 30 days"
        elif age >= 14:
            next_action = "Check claim status portal and verify no missing docs"
            status = "Follow up this week"
        else:
            next_action = "Monitor for adjudication"
            status = "Recently submitted"

        worklist.append(
            {
                "claim_id": claim.claim_id or "Unknown",
                "patient": f"{claim.patient.first_name} {claim.patient.last_name}".strip() or "Unknown",
                "payer": claim.payer_name or "Unknown",
                "risk": validation.get("denial_risk_level", "UNKNOWN"),
                "status": status,
                "days_since_submission": age,
                "next_action": next_action,
            }
        )
    return worklist


def build_team_dashboard(analyses: List[object]) -> Dict[str, object]:
    issue_counter = Counter()
    payer_counter = Counter()
    risk_counter = Counter()
    total_value = 0.0

    for item in analyses:
        claim = item.claim
        validation = item.validation
        payer_counter[claim.payer_name or "Unknown"] += 1
        risk_counter[validation.get("denial_risk_level", "UNKNOWN")] += 1
        total_value += claim.claim_amount
        for issue in validation.get("issues", []):
            issue_counter[issue.get("field") or "claim"] += 1

    return {
        "total_claim_value": round(total_value, 2),
        "top_issue_fields": issue_counter.most_common(5),
        "payer_mix": dict(payer_counter),
        "risk_mix": dict(risk_counter),
    }


def pricing_tiers() -> List[Dict[str, object]]:
    return [
        {
            "plan": "Starter",
            "price": "$49/mo",
            "best_for": "Solo billers and small practices",
            "features": [
                "Single-claim scrubber",
                "Basic denial risk scoring",
                "Appeal letter drafts",
                "Downloadable claim summary",
            ],
        },
        {
            "plan": "Pro",
            "price": "$199/mo",
            "best_for": "Billing teams and multi-provider clinics",
            "features": [
                "Everything in Starter",
                "Batch claim triage",
                "Payer-specific validation packs",
                "Prior auth and document checklist",
                "Team dashboard and aging worklist",
            ],
        },
        {
            "plan": "Enterprise",
            "price": "Custom",
            "best_for": "RCM teams and billing service companies",
            "features": [
                "Everything in Pro",
                "Custom payer rule packs",
                "Integration exports / webhook payloads",
                "Shared work queues",
                "White-label deployment support",
            ],
        },
    ]


PLAN_FEATURES = {
    "Starter": {"appeal_letter", "claim_scrubber", "save_report"},
    "Pro": {
        "appeal_letter",
        "claim_scrubber",
        "save_report",
        "payer_pack",
        "docs_checklist",
        "follow_up",
        "batch_triage",
        "team_dashboard",
    },
    "Enterprise": {
        "appeal_letter",
        "claim_scrubber",
        "save_report",
        "payer_pack",
        "docs_checklist",
        "follow_up",
        "batch_triage",
        "team_dashboard",
        "integrations",
        "shared_workqueues",
    },
}


def plan_has_feature(plan_name: str, feature_key: str) -> bool:
    return feature_key in PLAN_FEATURES.get(plan_name, set())


def generate_claim_report(item: object, guidance: str) -> Dict[str, object]:
    claim = item.claim
    validation = item.validation
    return {
        "claim_id": claim.claim_id,
        "payer": claim.payer_name,
        "patient": f"{claim.patient.first_name} {claim.patient.last_name}".strip(),
        "provider": f"{claim.provider.first_name} {claim.provider.last_name}".strip(),
        "service_date": claim.service_date,
        "claim_amount": claim.claim_amount,
        "source": item.source_label,
        "risk_level": validation.get("denial_risk_level"),
        "risk_score": validation.get("denial_risk_score"),
        "is_valid": validation.get("is_valid"),
        "issues": validation.get("issues", []),
        "suggested_corrections": getattr(item, "suggested_corrections", []),
        "documentation_checklist": getattr(item, "documentation_checklist", []),
        "appeal_letter": getattr(item, "appeal_letter", ""),
        "integration_payload": getattr(item, "integration_payload", {}),
        "guidance": guidance,
    }


def integration_payload(claim: Claim, validation: Dict) -> Dict[str, object]:
    return {
        "claim_id": claim.claim_id,
        "payer": claim.payer_name,
        "patient": {
            "first_name": claim.patient.first_name,
            "last_name": claim.patient.last_name,
            "insurance_id": claim.patient.insurance_id,
        },
        "provider": {
            "first_name": claim.provider.first_name,
            "last_name": claim.provider.last_name,
            "npi": claim.provider.npi,
        },
        "risk": {
            "level": validation.get("denial_risk_level"),
            "score": validation.get("denial_risk_score"),
        },
        "issues": validation.get("issues", []),
        "recommended_documents": documentation_checklist(claim, validation),
    }
