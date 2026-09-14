"""
backend/audit.py
=================
Append-only audit trail persisted to data_store/audit_log.json, backing the
Spectral-Lab Audit Log screen. Every Knowledge Base edit and every analysis
run appends an entry here.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.paths import AUDIT_LOG_PATH

_LOCK = threading.Lock()

MAX_ENTRIES = 2000


def _read() -> List[Dict[str, Any]]:
    try:
        with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _write(entries: List[Dict[str, Any]]) -> None:
    with open(AUDIT_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entries[:MAX_ENTRIES], f, indent=2)


def log_event(
    action: str,
    action_type: str,
    family_code: str = "-",
    user: str = "Lab Operator",
    user_role: str = "Snr. Metallurgist",
    change_from: str = "",
    change_to: str = "",
    impact_text: str = "",
    impact_type: str = "neutral",
) -> Dict[str, Any]:
    entry = {
        "id": f"audit-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "user": user,
        "userRole": user_role,
        "action": action,
        "actionType": action_type,
        "familyCode": family_code,
        "changeDetails": {"from": change_from, "to": change_to},
        "impactText": impact_text,
        "impactType": impact_type,
    }
    with _LOCK:
        entries = _read()
        entries.insert(0, entry)
        _write(entries)
    return entry


def list_events() -> List[Dict[str, Any]]:
    with _LOCK:
        return _read()
