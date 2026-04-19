"""
Local persistence helpers for demo product workflows.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict


BASE_DIR = Path(__file__).resolve().parent.parent / "runtime_data"
LEADS_FILE = BASE_DIR / "leads.jsonl"
REPORTS_DIR = BASE_DIR / "reports"


def ensure_runtime_dirs() -> None:
    BASE_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)


def _json_default(value: Any):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if is_dataclass(value):
        return asdict(value)
    return str(value)


def append_lead(lead: Dict[str, Any]) -> Path:
    ensure_runtime_dirs()
    payload = dict(lead)
    payload["captured_at"] = datetime.now().isoformat()
    with LEADS_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=_json_default) + "\n")
    return LEADS_FILE


def save_report(report_name: str, payload: Dict[str, Any]) -> Path:
    ensure_runtime_dirs()
    safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in report_name).strip("_") or "report"
    output_path = REPORTS_DIR / f"{safe_name}.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=_json_default)
    return output_path
