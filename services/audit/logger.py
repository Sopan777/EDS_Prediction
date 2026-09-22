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
