"""
services/audit/logger.py
========================
System audit log helper for Spectral Lab.
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from apps.history.models import AuditLog


def log_event(
    user_name: str = "Lab Operator",
    user_role: str = "Metallurgist",
    action: str = "General System Event",
    action_type: str = "Calibration",
    entity_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    impact_type: str = "neutral",
    user_id: str = "usr-current",
) -> str:
    """Record an audit trail event directly into SQLite via Django ORM."""
    log_id = f"audit-{int(time.time() * 1000)}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    AuditLog.objects.create(
        id=log_id,
        timestamp=now_str,
        user_id=user_id,
        user_name=user_name,
        user_role=user_role,
        action=action,
        action_type=action_type,
        entity_id=entity_id or "All",
        details_json=json.dumps(details or {}),
        impact_type=impact_type,
    )

    try:
        from services.audit.terminal_logger import ANSI, get_terminal_logger
        tlog = get_terminal_logger("dhatu_bodh.audit")
        imp_col = ANSI.GREEN if impact_type == "positive" else (ANSI.RED if impact_type == "negative" else ANSI.YELLOW)
        tlog.info(
            f"{ANSI.BG_CYAN} AUDIT {ANSI.RESET} "
            f"{imp_col}{ANSI.BOLD}[{action_type}]{ANSI.RESET} "
            f"{ANSI.CYAN}({entity_id or 'All'}){ANSI.RESET} "
            f"{ANSI.WHITE}{action}{ANSI.RESET} "
            f"{ANSI.GRAY}by {user_name} ({user_role}){ANSI.RESET}"
        )
    except Exception:
        pass

    return log_id


def get_audit_logs(
    action_type: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    qs = AuditLog.objects.all()
    if action_type and action_type != "All":
        qs = qs.filter(action_type=action_type)
    logs = qs[:limit]
    return [log.to_frontend_dict() for log in logs]
