"""
database.py
===========
SQLite persistence layer for Spectral Lab - MaterialID v2.4.
Manages:
  1. Analysis Reports (Specimen metadata, raw & normalized spectra, decision, candidates, caveats)
  2. Audit Logs (Full system traceability with timestamps and user attribution)
  3. Calibrated Ratio Gates (Family stoichiometric thresholds)
  4. Lab Personnel / Users (Roster and active session tracking)
  5. Standard Alloy Presets (Official metallurgical reference templates)
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent
DB_PATH = REPO_ROOT / "spectral_lab.db"


def get_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(reset: bool = False) -> None:
    """Initialize database tables and seed baseline admin and reference presets."""
    conn = get_connection()
    cur = conn.cursor()

    if reset:
        cur.execute("DROP TABLE IF EXISTS reports")
        cur.execute("DROP TABLE IF EXISTS audit_logs")
        cur.execute("DROP TABLE IF EXISTS ratio_gates")
        cur.execute("DROP TABLE IF EXISTS users")
        cur.execute("DROP TABLE IF EXISTS alloy_presets")
        cur.execute("DROP TABLE IF EXISTS prediction_feedback")
        cur.execute("DROP TABLE IF EXISTS analysis_history")

    # 1. Reports Table (Full Specimen Analysis Records)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            sample_id TEXT NOT NULL,
            lot_number TEXT,
            customer TEXT,
            analyst_id TEXT NOT NULL,
            analyst_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_filename TEXT,
            raw_composition_json TEXT NOT NULL,
            normalized_composition_json TEXT NOT NULL,
            decision TEXT NOT NULL,
            family_id TEXT,
            family_label TEXT,
            grade_hint TEXT,
            compatibility_pct REAL NOT NULL,
            candidates_json TEXT,
            caveats_json TEXT,
            analyst_notes TEXT,
            status TEXT NOT NULL DEFAULT 'Completed'
        )
    """)

    # 2. Audit Logs Table (Traceability & System Events)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            user_id TEXT NOT NULL,
            user_name TEXT NOT NULL,
            user_role TEXT NOT NULL,
            action TEXT NOT NULL,
            action_type TEXT NOT NULL,
            entity_id TEXT,
            details_json TEXT,
            impact_type TEXT NOT NULL DEFAULT 'neutral'
        )
    """)

    # 3. Ratio Gates Overrides Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ratio_gates (
            id TEXT PRIMARY KEY,
            family_id TEXT NOT NULL,
            name TEXT NOT NULL,
            numerator TEXT NOT NULL,
            denominator TEXT NOT NULL,
            min_val REAL NOT NULL,
            max_val REAL NOT NULL,
            rationale TEXT,
            enabled INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL,
            updated_by TEXT NOT NULL
        )
    """)

    # 4. Users / Personnel Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT NOT NULL,
            department TEXT NOT NULL,
            permissions TEXT NOT NULL,
            initials TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            last_active TEXT
        )
    """)

    # 5. Alloy Presets Table (Reference Templates)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alloy_presets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            composition_json TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # 6. Prediction Feedback Table (Analyst Confirmations and Corrections)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prediction_feedback (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            analysis_id TEXT,
            spectrum_json TEXT NOT NULL,
            predicted_family TEXT NOT NULL,
            predicted_component TEXT,
            confirmed_family TEXT NOT NULL,
            confirmed_component TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'confirmed',
            analyst_name TEXT NOT NULL,
            notes TEXT
        )
    """)

    # 7. Analysis History Table (Historical Runs for Dashboard & History View)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            source_type TEXT NOT NULL,
            filename TEXT,
            composition_json TEXT NOT NULL,
            decision TEXT NOT NULL,
            material_family TEXT,
            grade_hint TEXT,
            compatibility REAL,
            candidate_components_json TEXT,
            processing_time_s REAL
        )
    """)

    # Clean seed: Lead Metallurgist (Administrator account)
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "usr-admin",
            "Lead Metallurgist",
            "metallurgy@spectrallab.io",
            "Chief Metallurgist",
            "Failure Analysis & Metallurgy",
            "Full Admin",
            "LM",
            1,
            now_str,
            "Active Now",
        ))

    # Clean seed: Official Metallurgical Reference Templates
    cur.execute("SELECT COUNT(*) FROM alloy_presets")
    if cur.fetchone()[0] == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        default_presets = [
            (
                "preset-304",
                "Austenitic 304 SS",
                "Stainless Steel",
                "Nominal AISI 304 / 1.4301 (18/8 austenitic Cr-Ni steel)",
                json.dumps({"Cr": 18.2, "Ni": 8.4, "Mn": 1.6, "Si": 0.5, "Fe": 71.3}),
                "Standard Reference",
                now_str,
            ),
            (
                "preset-bronze",
                "Cu-Sn Bronze (F6a)",
                "Non-Ferrous Alloy",
                "Cu-Sn bronze metal matrix (bearing Bush / thrust washers)",
                json.dumps({"Cu": 88.5, "Sn": 10.5, "P": 0.4, "Fe": 0.3}),
                "Standard Reference",
                now_str,
            ),
            (
                "preset-15mn",
                "1.5Mn Steel (F1b)",
                "Carbon Steel",
                "16MnCr5 case hardening plain carbon steel",
                json.dumps({"Mn": 1.48, "Cr": 0.15, "Si": 0.25, "C": 0.45, "Fe": 97.67}),
                "Standard Reference",
                now_str,
            ),
            (
                "preset-bearing",
                "100Cr6 Bearing Steel (F2)",
                "Low-Alloy Steel",
                "High-carbon chromium bearing steel (100Cr6 / AISI 52100)",
                json.dumps({"Cr": 1.45, "Mn": 0.35, "Si": 0.25, "Ni": 0.05, "C": 1.0, "Fe": 96.9}),
                "Standard Reference",
                now_str,
            ),
            (
                "preset-zn-coat",
                "Zn-Phosphate Coating (F8b)",
                "Surface Treatment",
                "Zinc phosphate conversion coating layer on steel substrate",
                json.dumps({"Zn": 12.0, "P": 4.5, "Fe": 83.5}),
                "Standard Reference",
                now_str,
            ),
        ]
        cur.executemany("""
            INSERT INTO alloy_presets VALUES (?, ?, ?, ?, ?, ?, ?)
        """, default_presets)

    conn.commit()
    conn.close()


# --------------------------------------------------------------------------
# Reports Management API
# --------------------------------------------------------------------------
def save_report(
    title: str,
    sample_id: str,
    analyst_id: str,
    analyst_name: str,
    source_type: str,
    raw_composition: Dict[str, float],
    normalized_composition: List[Dict[str, Any]],
    decision: str,
    family_id: Optional[str],
    family_label: Optional[str],
    grade_hint: Optional[str],
    compatibility_pct: float,
    candidates: List[str],
    caveats: List[str],
    lot_number: Optional[str] = None,
    customer: Optional[str] = None,
    source_filename: Optional[str] = None,
    analyst_notes: Optional[str] = None,
    status: str = "Completed",
) -> str:
    """Save an official analysis report into the database."""
    conn = get_connection()
    cur = conn.cursor()

    report_id = f"RPT-{datetime.now().strftime('%Y%m%d')}-{int(time.time() % 10000):04d}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO reports VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """, (
        report_id,
        title or f"Microanalysis of {sample_id}",
        sample_id,
        lot_number or "N/A",
        customer or "Internal Lab",
        analyst_id,
        analyst_name,
        now_str,
        source_type,
        source_filename,
        json.dumps(raw_composition),
        json.dumps(normalized_composition),
        decision,
        family_id,
        family_label,
        grade_hint,
        compatibility_pct,
        json.dumps(candidates),
        json.dumps(caveats),
        analyst_notes or "",
        status,
    ))

    # Log audit event
    log_audit(
        user_id=analyst_id,
        user_name=analyst_name,
        user_role="Analyst",
        action=f"Created official analysis report '{report_id}' for sample {sample_id}",
        action_type="REPORT_CREATION",
        entity_id=report_id,
        details={"sample_id": sample_id, "family": family_label, "decision": decision},
        impact_type="positive" if decision == "identified" else "neutral",
        conn=conn,
    )

    conn.commit()
    conn.close()
    return report_id


def get_reports(
    status: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Retrieve stored analysis reports with optional status and search filters."""
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT * FROM reports WHERE 1=1"
    params: List[Any] = []

    if status and status != "All":
        query += " AND status = ?"
        params.append(status)

    if search_query:
        q = f"%{search_query.strip()}%"
        query += " AND (sample_id LIKE ? OR title LIKE ? OR family_label LIKE ? OR customer LIKE ?)"
        params.extend([q, q, q, q])

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    reports = []
    for r in rows:
        reports.append({
            "id": r["id"],
            "title": r["title"],
            "sample_id": r["sample_id"],
            "lot_number": r["lot_number"],
            "customer": r["customer"],
            "analyst_id": r["analyst_id"],
            "analyst_name": r["analyst_name"],
            "created_at": r["created_at"],
            "source_type": r["source_type"],
            "source_filename": r["source_filename"],
            "raw_composition": json.loads(r["raw_composition_json"]),
            "normalized_composition": json.loads(r["normalized_composition_json"]),
            "decision": r["decision"],
            "family_id": r["family_id"],
            "family_label": r["family_label"],
            "grade_hint": r["grade_hint"],
            "compatibility_pct": r["compatibility_pct"],
            "candidates": json.loads(r["candidates_json"]) if r["candidates_json"] else [],
            "caveats": json.loads(r["caveats_json"]) if r["caveats_json"] else [],
            "analyst_notes": r["analyst_notes"],
            "status": r["status"],
        })
    return reports


def get_report_by_id(report_id: str) -> Optional[Dict[str, Any]]:
    """Fetch single report record by ID."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row["id"],
        "title": row["title"],
        "sample_id": row["sample_id"],
        "lot_number": row["lot_number"],
        "customer": row["customer"],
        "analyst_id": row["analyst_id"],
        "analyst_name": row["analyst_name"],
        "created_at": row["created_at"],
        "source_type": row["source_type"],
        "source_filename": row["source_filename"],
        "raw_composition": json.loads(row["raw_composition_json"]),
        "normalized_composition": json.loads(row["normalized_composition_json"]),
        "decision": row["decision"],
        "family_id": row["family_id"],
        "family_label": row["family_label"],
        "grade_hint": row["grade_hint"],
        "compatibility_pct": row["compatibility_pct"],
        "candidates": json.loads(row["candidates_json"]) if row["candidates_json"] else [],
        "caveats": json.loads(row["caveats_json"]) if row["caveats_json"] else [],
        "analyst_notes": row["analyst_notes"],
        "status": row["status"],
    }


def update_report_status(report_id: str, new_status: str, user_name: str = "Lead Metallurgist") -> bool:
    """Update report workflow status (Completed, Under Review, Approved)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE reports SET status = ? WHERE id = ?", (new_status, report_id))
    log_audit(
        user_id="usr-current",
        user_name=user_name,
        user_role="Lead Metallurgist",
        action=f"Updated report '{report_id}' status to {new_status}",
        action_type="REPORT_STATUS_UPDATE",
        entity_id=report_id,
        details={"new_status": new_status},
        conn=conn,
    )
    conn.commit()
    conn.close()
    return True


def delete_report(report_id: str, user_name: str = "Lead Metallurgist") -> bool:
    """Delete a report record from the database."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    log_audit(
        user_id="usr-current",
        user_name=user_name,
        user_role="Lead Metallurgist",
        action=f"Deleted report '{report_id}'",
        action_type="REPORT_DELETION",
        entity_id=report_id,
        impact_type="negative",
        conn=conn,
    )
    conn.commit()
    conn.close()
    return True


# --------------------------------------------------------------------------
# Audit Logging API
# --------------------------------------------------------------------------
def log_audit(
    user_id: str,
    user_name: str,
    user_role: str,
    action: str,
    action_type: str,
    entity_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    impact_type: str = "neutral",
    conn: Optional[sqlite3.Connection] = None,
) -> str:
    """Record an audit trail event."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    cur = conn.cursor()
    log_id = f"aud-{int(time.time() * 1000)}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO audit_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        log_id,
        now_str,
        user_id,
        user_name,
        user_role,
        action,
        action_type,
        entity_id,
        json.dumps(details or {}),
        impact_type,
    ))

    if should_close:
        conn.commit()
        conn.close()

    return log_id


def get_audit_logs(action_type: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
    """Fetch audit logs ordered by timestamp descending."""
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT * FROM audit_logs WHERE 1=1"
    params: List[Any] = []

    if action_type and action_type != "All":
        query += " AND action_type = ?"
        params.append(action_type)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    logs = []
    for r in rows:
        logs.append({
            "id": r["id"],
            "timestamp": r["timestamp"],
            "user_id": r["user_id"],
            "user_name": r["user_name"],
            "user_role": r["user_role"],
            "action": r["action"],
            "action_type": r["action_type"],
            "entity_id": r["entity_id"],
            "details": json.loads(r["details_json"]) if r["details_json"] else {},
            "impact_type": r["impact_type"],
        })
    return logs


# --------------------------------------------------------------------------
# Ratio Gates API
# --------------------------------------------------------------------------
def get_gates_for_family(family_id: str) -> Optional[List[Dict[str, Any]]]:
    """Fetch user-overridden ratio gates for a family from SQLite."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ratio_gates WHERE family_id = ?", (family_id,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return None

    return [
        {
            "id": r["id"],
            "family_id": r["family_id"],
            "name": r["name"],
            "numerator": r["numerator"],
            "denominator": r["denominator"],
            "min": r["min_val"],
            "max": r["max_val"],
            "rationale": r["rationale"] or "",
            "enabled": bool(r["enabled"]),
            "updated_at": r["updated_at"],
            "updated_by": r["updated_by"],
        }
        for r in rows
    ]


def save_gates_for_family(
    family_id: str,
    gates: List[Dict[str, Any]],
    user_name: str = "Lead Metallurgist",
) -> None:
    """Save calibrated ratio gates for a family and log audit."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM ratio_gates WHERE family_id = ?", (family_id,))
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for g in gates:
        cur.execute("""
            INSERT INTO ratio_gates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            g["id"],
            family_id,
            g["name"],
            g["numerator"],
            g["denominator"],
            g["min"],
            g["max"],
            g.get("rationale", ""),
            1 if g.get("enabled", True) else 0,
            now_str,
            user_name,
        ))

    log_audit(
        user_id="usr-current",
        user_name=user_name,
        user_role="Lead Metallurgist",
        action=f"Calibrated {len(gates)} ratio gates for {family_id}",
        action_type="GATE_CALIBRATION",
        entity_id=family_id,
        details={"family_id": family_id, "gates_count": len(gates)},
        impact_type="positive",
        conn=conn,
    )

    conn.commit()
    conn.close()


def reset_gates_for_family(family_id: str, user_name: str = "Lead Metallurgist") -> None:
    """Reset gates for a family to defaults by deleting overrides."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM ratio_gates WHERE family_id = ?", (family_id,))
    log_audit(
        user_id="usr-current",
        user_name=user_name,
        user_role="Lead Metallurgist",
        action=f"Reset ratio gates for {family_id} to standard defaults",
        action_type="GATE_CALIBRATION",
        entity_id=family_id,
        conn=conn,
    )
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------
# Users / Personnel API
# --------------------------------------------------------------------------
def get_users() -> List[Dict[str, Any]]:
    """Fetch active personnel roster."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE is_active = 1 ORDER BY name ASC")
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "email": r["email"],
            "role": r["role"],
            "department": r["department"],
            "permissions": r["permissions"],
            "initials": r["initials"],
            "is_active": r["is_active"],
            "created_at": r["created_at"],
            "last_active": r["last_active"] or "Recently",
        }
        for r in rows
    ]


def add_user(
    name: str,
    email: str,
    role: str,
    department: str,
    permissions: str,
    initials: Optional[str] = None,
    created_by: str = "Lead Metallurgist",
) -> str:
    """Register a new lab analyst."""
    conn = get_connection()
    cur = conn.cursor()

    user_id = f"usr-{int(time.time() % 100000):05d}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    init = initials.upper() if initials else "".join([p[0] for p in name.split()[:2]]).upper()

    cur.execute("""
        INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        name,
        email,
        role,
        department,
        permissions,
        init,
        1,
        now_str,
        "Registered Just Now",
    ))

    log_audit(
        user_id="usr-current",
        user_name=created_by,
        user_role="Admin",
        action=f"Registered new lab personnel: {name} ({role})",
        action_type="USER_MANAGEMENT",
        entity_id=user_id,
        details={"name": name, "email": email, "role": role},
        conn=conn,
    )

    conn.commit()
    conn.close()
    return user_id


# --------------------------------------------------------------------------
# Alloy Presets API
# --------------------------------------------------------------------------
def get_presets() -> List[Dict[str, Any]]:
    """Fetch saved alloy composition templates."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM alloy_presets ORDER BY name ASC")
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "category": r["category"],
            "description": r["description"] or "",
            "composition": json.loads(r["composition_json"]),
            "created_by": r["created_by"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def add_preset(
    name: str,
    category: str,
    description: str,
    composition: Dict[str, float],
    created_by: str = "Lead Metallurgist",
) -> str:
    """Save a new alloy composition template."""
    conn = get_connection()
    cur = conn.cursor()

    preset_id = f"preset-{int(time.time() % 100000):05d}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO alloy_presets VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        preset_id,
        name,
        category,
        description,
        json.dumps(composition),
        created_by,
        now_str,
    ))

    conn.commit()
    conn.close()
    return preset_id


# ==========================================
# 6. Prediction Feedback CRUD API
# ==========================================

def save_feedback(
    predicted_family: str,
    confirmed_family: str,
    confirmed_component: str,
    spectrum: Dict[str, float],
    predicted_component: Optional[str] = None,
    analysis_id: Optional[str] = None,
    status: str = "confirmed",
    analyst_name: str = "Lab Metallurgist",
    notes: str = "",
) -> str:
    """Save an analyst confirmation or correction of a prediction."""
    conn = get_connection()
    cur = conn.cursor()

    feedback_id = f"fb-{int(time.time() * 1000)}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO prediction_feedback VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        feedback_id,
        now_str,
        analysis_id,
        json.dumps(spectrum),
        predicted_family,
        predicted_component,
        confirmed_family,
        confirmed_component,
        status,
        analyst_name,
        notes,
    ))

    conn.commit()
    conn.close()
    return feedback_id


def get_all_feedback(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieve recent prediction feedback records."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM prediction_feedback ORDER BY timestamp DESC LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()

    out = []
    for r in rows:
        d = dict(r)
        try:
            d["spectrum"] = json.loads(d["spectrum_json"])
        except Exception:
            d["spectrum"] = {}
        out.append(d)
    return out


# Initialize database automatically
init_db()
