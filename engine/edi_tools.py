"""
Compact EDI inspection tools for 837 validation, 835 denial analysis, and EDI-to-JSON conversion.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional

from engine.parser import EDI837Parser


COMMON_CARC = {
    "16": "Claim/service lacks information or has submission/billing error(s).",
    "45": "Charge exceeds fee schedule or maximum allowable amount.",
    "96": "Non-covered charge(s).",
    "197": "Payment adjusted for absence of precertification/authorization.",
}

COMMON_RARC = {
    "M15": "Separately billed services/tests have been bundled.",
    "N30": "Patient ineligible for this service on this date.",
    "N115": "Service adjusted because a related service was processed first.",
}


def detect_delimiters(raw: str) -> Dict[str, str]:
    stripped = raw.strip()
    if len(stripped) >= 4 and stripped.startswith("ISA"):
        element = stripped[3]
    else:
        element = "*"

    segment = "~" if "~" in stripped else "\n"
    component = ":" if ":" in stripped else ">"
    repetition = "^" if "^" in stripped else ""
    return {
        "element": element,
        "segment": segment,
        "component": component,
        "repetition": repetition,
    }


def split_segments(raw: str) -> List[str]:
    delimiters = detect_delimiters(raw)
    segment_sep = delimiters["segment"]
    normalized = raw.replace("\r", "").strip()
    return [segment.strip() for segment in normalized.split(segment_sep) if segment.strip()]


def parse_edi_json(raw: str) -> Dict:
    delimiters = detect_delimiters(raw)
    segments = split_segments(raw)
    parsed_segments = []
    for index, segment in enumerate(segments, start=1):
        parts = segment.split(delimiters["element"])
        parsed_segments.append(
            {
                "index": index,
                "tag": parts[0],
                "elements": parts[1:],
                "raw": segment,
            }
        )

    tags = [item["tag"] for item in parsed_segments]
    transaction_type = "835" if "CLP" in tags or "CAS" in tags else "837" if "CLM" in tags else "unknown"
    return {
        "delimiters": delimiters,
        "transaction_type": transaction_type,
        "segment_count": len(parsed_segments),
        "segments": parsed_segments,
    }


def _error(segment: str, field: str, expected: str, actual: str, explanation: str, fix: str, severity: str = "HIGH") -> Dict:
    return {
        "segment": segment,
        "field": field,
        "expected": expected,
        "actual": actual,
        "explanation": explanation,
        "fix": fix,
        "severity": severity,
    }


def validate_837(raw: str) -> Dict:
    parser = EDI837Parser()
    parsed = parser.parse(raw)
    generic = parse_edi_json(raw)
    segments = generic["segments"]
    errors: List[Dict] = []

    tags = [segment["tag"] for segment in segments]
    if "NM1" not in tags:
        errors.append(
            _error(
                "NM1",
                "loop",
                "At least one NM1 segment",
                "Missing",
                "The file is missing a required name segment for a billing provider or subscriber.",
                "Add the required NM1 segments for provider and subscriber/patient.",
                "CRITICAL",
            )
        )
    if "CLM" not in tags:
        errors.append(
            _error(
                "CLM",
                "CLM01",
                "At least one claim segment",
                "Missing",
                "The file is missing claim-level information.",
                "Add a CLM segment for each claim.",
                "CRITICAL",
            )
        )
    if "HI" not in tags:
        errors.append(
            _error(
                "HI",
                "HI01",
                "At least one diagnosis segment",
                "Missing",
                "Diagnosis information is required for claim submission.",
                "Add HI segments with the diagnosis codes that support the billed service.",
                "CRITICAL",
            )
        )

    clm_ids = []
    for claim in parsed.get("claims", []):
        claim_id = claim.get("claim_id")
        if claim_id:
            clm_ids.append(claim_id)
    duplicate_ids = [claim_id for claim_id, count in Counter(clm_ids).items() if count > 1]
    for claim_id in duplicate_ids:
        errors.append(
            _error(
                "CLM",
                "CLM01",
                "Unique claim identifier",
                claim_id,
                "Duplicate CLM01 values increase rejection risk because the payer may treat the claim as a duplicate.",
                "Assign a unique claim ID to each CLM segment.",
                "HIGH",
            )
        )

    for segment in segments:
        if segment["tag"] == "NM1" and len(segment["elements"]) >= 9:
            qualifier = segment["elements"][7] if len(segment["elements"]) >= 8 else ""
            npi = segment["elements"][8]
            if qualifier == "XX" and not re.fullmatch(r"\d{10}", npi or ""):
                errors.append(
                    _error(
                        "NM1",
                        "NM109",
                        "10-digit NPI",
                        npi or "Missing",
                        "NM109 should contain a 10-digit NPI when the qualifier is XX.",
                        "Replace NM109 with a valid NPPES-issued 10-digit NPI.",
                        "HIGH",
                    )
                )

        if segment["tag"] == "HI":
            for pos, element in enumerate(segment["elements"], start=1):
                if ":" in element:
                    code = element.split(":")[-1].strip().upper()
                    if code and not re.fullmatch(r"[A-Z]\d{2}(?:\.[A-Z0-9]{1,4})?", code):
                        errors.append(
                            _error(
                                "HI",
                                f"HI{pos:02d}",
                                "ICD-10 code format",
                                code,
                                "The diagnosis code format looks invalid for ICD-10-CM.",
                                "Use a valid ICD-10 diagnosis code such as M54.50 or Z23.",
                                "MEDIUM",
                            )
                        )

        if segment["tag"] == "SV1" and segment["elements"]:
            first = segment["elements"][0]
            proc = first.split(":")[-1].strip().upper()
            if proc and not re.fullmatch(r"[A-Z0-9]{5}", proc):
                errors.append(
                    _error(
                        "SV1",
                        "SV101",
                        "5-character CPT/HCPCS code",
                        proc,
                        "The procedure code should be a 5-character CPT or HCPCS-style code.",
                        "Replace the procedure code with a valid CPT/HCPCS code.",
                        "MEDIUM",
                    )
                )

    missing_order_pairs = [("ST", "SE"), ("GS", "GE"), ("ISA", "IEA")]
    for start_tag, end_tag in missing_order_pairs:
        if start_tag in tags and end_tag not in tags:
            errors.append(
                _error(
                    end_tag,
                    "segment",
                    f"{end_tag} trailer present",
                    "Missing",
                    f"{start_tag} was found but the matching trailer {end_tag} is missing.",
                    f"Add the {end_tag} trailer to close the interchange/group/transaction correctly.",
                    "HIGH",
                )
            )

    explanation = _build_837_summary(errors, parsed)
    return {
        "kind": "837_validation",
        "parsed_json": generic,
        "parsed_claims": parsed,
        "errors": errors,
        "error_count": len(errors),
        "summary": explanation,
    }


def _build_837_summary(errors: List[Dict], parsed: Dict) -> str:
    if not errors:
        return "The 837 structure passed the current validator checks. Review payer-specific rules before submission."
    top = errors[:3]
    bullets = "\n".join(f"- {item['segment']} {item['field']}: {item['explanation']}" for item in top)
    return (
        f"Found {len(errors)} validation issue(s) across {parsed.get('total_claims', 0)} claim(s).\n"
        f"Most important fixes:\n{bullets}"
    )


def analyze_835(raw: str) -> Dict:
    parsed = parse_edi_json(raw)
    segments = parsed["segments"]
    clp_claims = []
    carc_counts = Counter()
    carc_amounts = defaultdict(float)
    rarc_counts = Counter()

    current_claim_id = None
    for segment in segments:
        if segment["tag"] == "CLP":
            claim_id = segment["elements"][0] if segment["elements"] else "Unknown"
            status_code = segment["elements"][1] if len(segment["elements"]) > 1 else ""
            charge = _to_float(segment["elements"][2] if len(segment["elements"]) > 2 else 0)
            payment = _to_float(segment["elements"][3] if len(segment["elements"]) > 3 else 0)
            patient_resp = _to_float(segment["elements"][4] if len(segment["elements"]) > 4 else 0)
            clp_claims.append(
                {
                    "claim_id": claim_id,
                    "claim_status_code": status_code,
                    "total_charge": charge,
                    "payment_amount": payment,
                    "patient_responsibility": patient_resp,
                }
            )
            current_claim_id = claim_id

        elif segment["tag"] == "CAS":
            group_code = segment["elements"][0] if segment["elements"] else ""
            elements = segment["elements"][1:]
            for idx in range(0, len(elements), 3):
                reason_code = elements[idx] if idx < len(elements) else ""
                amount = _to_float(elements[idx + 1] if idx + 1 < len(elements) else 0)
                quantity = elements[idx + 2] if idx + 2 < len(elements) else ""
                if reason_code:
                    carc_counts[reason_code] += 1
                    carc_amounts[reason_code] += amount
            if clp_claims:
                clp_claims[-1].setdefault("adjustments", []).append({"group_code": group_code, "elements": segment["elements"]})

        elif segment["tag"] == "LQ":
            qualifier = segment["elements"][0] if segment["elements"] else ""
            code = segment["elements"][1] if len(segment["elements"]) > 1 else ""
            if qualifier == "HE" and code:
                rarc_counts[code] += 1
                if clp_claims:
                    clp_claims[-1].setdefault("remark_codes", []).append(code)

    top_denials = [
        {
            "carc_code": code,
            "count": count,
            "financial_impact": round(carc_amounts[code], 2),
            "meaning": COMMON_CARC.get(code, "CARC meaning not mapped in the lightweight catalog yet."),
        }
        for code, count in carc_counts.most_common(5)
    ]

    remarks = [
        {
            "rarc_code": code,
            "count": count,
            "meaning": COMMON_RARC.get(code, "RARC meaning not mapped in the lightweight catalog yet."),
        }
        for code, count in rarc_counts.most_common(5)
    ]

    summary = _build_835_summary(top_denials, remarks, clp_claims)
    return {
        "kind": "835_analysis",
        "parsed_json": parsed,
        "claims": clp_claims,
        "top_denials": top_denials,
        "remark_codes": remarks,
        "financial_impact_total": round(sum(carc_amounts.values()), 2),
        "summary": summary,
    }


def _to_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _build_835_summary(top_denials: List[Dict], remarks: List[Dict], claims: List[Dict]) -> str:
    if not top_denials and not claims:
        return "No CLP/CAS denial information was detected in the uploaded 835."
    lead = top_denials[0] if top_denials else None
    if lead:
        return (
            f"Processed {len(claims)} remittance claim(s). "
            f"Top denial/adjustment driver is CARC {lead['carc_code']} "
            f"({lead['count']} occurrence(s), ${lead['financial_impact']:.2f} impact)."
        )
    return f"Processed {len(claims)} remittance claim(s) with remark activity but no mapped CARC summary."
