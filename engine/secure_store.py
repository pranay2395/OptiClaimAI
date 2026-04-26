"""
Secure local storage helpers for product artifacts.

Design goals:
- persist the minimum necessary data
- encrypt PHI-bearing artifacts at rest
- keep a short retention window for local runtime storage
- write a lightweight audit trail without raw PHI
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from cryptography.fernet import Fernet
except ImportError:  # pragma: no cover - fallback for thin runtimes
    Fernet = None


BASE_DIR = Path(__file__).resolve().parent.parent / "runtime_data"
PHI_REPORTS_DIR = BASE_DIR / "secure_reports"
LEADS_FILE = BASE_DIR / "leads.jsonl"
AUDIT_FILE = BASE_DIR / "audit.jsonl"
USAGE_FILE = BASE_DIR / "usage.json"
DEFAULT_RETENTION_HOURS = int(os.getenv("OPTICLAIM_RETENTION_HOURS", "24"))

_runtime_key: Optional[bytes] = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_runtime_dirs() -> None:
    BASE_DIR.mkdir(exist_ok=True)
    PHI_REPORTS_DIR.mkdir(exist_ok=True)


def _json_default(value: Any):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if is_dataclass(value):
        return asdict(value)
    return str(value)


def _key_material() -> bytes:
    """
    Resolve the encryption key.

    Production path: set OPTICLAIM_MASTER_KEY to a Fernet-compatible base64 key
    stored in a secret manager / KMS-backed environment secret.
    Fallback path: generate an ephemeral runtime key.
    """
    global _runtime_key
    configured = os.getenv("OPTICLAIM_MASTER_KEY", "").strip()
    if configured:
        return configured.encode("utf-8")
    if _runtime_key is None:
        if Fernet is None:
            raise RuntimeError("Encrypted PHI storage requires the 'cryptography' package.")
        _runtime_key = Fernet.generate_key()
    return _runtime_key


def _fernet() -> Fernet:
    if Fernet is None:
        raise RuntimeError("Encrypted PHI storage requires the 'cryptography' package.")
    return Fernet(_key_material())


def _hash_identifier(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _mask_email(email: str) -> str:
    if "@" not in email:
        return email[:2] + "***"
    local, domain = email.split("@", 1)
    return (local[:2] + "***@" + domain) if local else "***@" + domain


def _mask_name(name: str) -> str:
    if not name:
        return ""
    parts = name.split()
    return " ".join(part[:1] + "***" for part in parts)


def write_audit_event(event_type: str, metadata: Dict[str, Any]) -> Path:
    ensure_runtime_dirs()
    payload = {
        "timestamp": _now().isoformat(),
        "event_type": event_type,
        "metadata": metadata,
    }
    with AUDIT_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=_json_default) + "\n")
    return AUDIT_FILE


def append_lead(lead: Dict[str, Any]) -> Path:
    """
    Sales leads should avoid PHI entirely. Persist business contact data only.
    """
    ensure_runtime_dirs()
    payload = {
        "captured_at": _now().isoformat(),
        "name": lead.get("name", "").strip(),
        "email": lead.get("email", "").strip(),
        "company": lead.get("company", "").strip(),
        "interested_plan": lead.get("interested_plan", "").strip(),
        "use_case": lead.get("use_case", "").strip(),
    }
    with LEADS_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=_json_default) + "\n")
    write_audit_event(
        "lead_captured",
        {
            "company": payload["company"],
            "plan": payload["interested_plan"],
            "name_masked": _mask_name(payload["name"]),
            "email_masked": _mask_email(payload["email"]),
        },
    )
    return LEADS_FILE


def secure_report_name(report_name: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in report_name).strip("_")
    return safe or "report"


def save_encrypted_report(report_name: str, payload: Dict[str, Any], retention_hours: int = DEFAULT_RETENTION_HOURS) -> Path:
    if Fernet is None:
        raise RuntimeError("Encrypted PHI storage is unavailable because the 'cryptography' package is not installed.")
    ensure_runtime_dirs()
    expires_at = _now() + timedelta(hours=retention_hours)
    body = json.dumps(payload, default=_json_default).encode("utf-8")
    ciphertext = _fernet().encrypt(body)

    file_stem = secure_report_name(report_name)
    output_path = PHI_REPORTS_DIR / f"{file_stem}.bin"
    envelope = {
        "created_at": _now().isoformat(),
        "expires_at": expires_at.isoformat(),
        "ciphertext": base64.urlsafe_b64encode(ciphertext).decode("utf-8"),
    }
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(envelope, handle, indent=2)

    write_audit_event(
        "secure_report_saved",
        {
            "report_id": _hash_identifier(file_stem),
            "retention_hours": retention_hours,
        },
    )
    return output_path


def cleanup_expired_reports() -> int:
    ensure_runtime_dirs()
    removed = 0
    now = _now()
    for path in PHI_REPORTS_DIR.glob("*.bin"):
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            expires_at = datetime.fromisoformat(envelope["expires_at"])
            if expires_at <= now:
                path.unlink(missing_ok=True)
                removed += 1
        except Exception:
            path.unlink(missing_ok=True)
            removed += 1

    if removed:
        write_audit_event("secure_report_cleanup", {"removed": removed})
    return removed


def storage_status() -> Dict[str, Any]:
    configured = bool(os.getenv("OPTICLAIM_MASTER_KEY", "").strip())
    return {
        "encrypted_storage": Fernet is not None,
        "retention_hours": DEFAULT_RETENTION_HOURS,
        "master_key_configured": configured,
        "mode": (
            "configured-key"
            if configured and Fernet is not None
            else "ephemeral-dev-key"
            if Fernet is not None
            else "crypto-missing"
        ),
    }


def _load_usage() -> Dict[str, Any]:
    ensure_runtime_dirs()
    if not USAGE_FILE.exists():
        return {}
    try:
        return json.loads(USAGE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_usage(data: Dict[str, Any]) -> None:
    ensure_runtime_dirs()
    USAGE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_daily_usage(counter_key: str) -> int:
    today = date.today().isoformat()
    usage = _load_usage()
    bucket = usage.get(counter_key, {})
    if bucket.get("date") != today:
        bucket = {"date": today, "count": 0}
        usage[counter_key] = bucket
        _save_usage(usage)
    return int(bucket.get("count", 0))


def increment_daily_usage(counter_key: str) -> int:
    today = date.today().isoformat()
    usage = _load_usage()
    bucket = usage.get(counter_key, {})
    if bucket.get("date") != today:
        bucket = {"date": today, "count": 0}
    bucket["count"] = int(bucket.get("count", 0)) + 1
    bucket["date"] = today
    usage[counter_key] = bucket
    _save_usage(usage)
    write_audit_event("usage_incremented", {"counter_key": counter_key, "count": bucket["count"]})
    return bucket["count"]
