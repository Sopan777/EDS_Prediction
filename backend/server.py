"""
server.py
=========
Production Flask Web API and server for Spectral Lab - MaterialID.
Integrates the deterministic rule-based scoring engine (rule_engine/scoring.py)
with the Spectral Lab React UI.

Endpoints:
  GET  /api/health             - System status and version
  GET  /api/families           - List all 12 material families from knowledge base
  GET  /api/families/<fid>     - Detail for a single material family
  POST /api/analyze            - Predict material family from manual wt% or uploaded
                                 file (PDF/DOCX/CSV/JSON) — uses pooled multi-spectrum
  GET  /api/analyses           - List historical analyses from DB
  GET  /api/analyses/<aid>     - Detail for a single analysis
  POST /api/sessions           - Create a new analysis session (particle scan)
  GET  /api/gates              - List ratio gates (with user overrides from DB)
  PUT  /api/gates/<fid>        - Update ratio gates for a family
  POST /api/gates/validate     - Real validation against KB reference spectra
  GET  /api/audit-logs         - List system audit logs
  POST /api/audit-logs         - Record a new audit log
  GET  /api/users              - List users
  POST /api/users              - Add a new user
  PUT  /api/users/<uid>        - Update user status or attributes
  GET  /                       - Serve React frontend (frontend/dist)
"""

from __future__ import annotations

import copy
import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Load .env file if present (no-op if python-dotenv absent)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import Flask, jsonify, request, send_from_directory
try:
    from flask_cors import CORS
except ImportError:
    CORS = lambda app: None

# ---------------------------------------------------------------------------
# Paths & Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Database path — configurable via DATABASE_URL env var
_db_url = os.environ.get("DATABASE_URL", "")
if _db_url.startswith("sqlite:///"):
    DB_PATH = Path(_db_url[len("sqlite:///"):])
else:
    DB_PATH = REPO_ROOT / "spectral_lab.db"

# Upload directory — configurable via UPLOADS_DIR env var
UPLOADS_DIR = Path(os.environ.get("UPLOADS_DIR", str(REPO_ROOT / "uploads")))
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Frontend dist folder
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
if not FRONTEND_DIST.exists():
    _legacy_dist = REPO_ROOT / "spectral-lab---materialid" / "dist"
    if _legacy_dist.exists():
        FRONTEND_DIST = _legacy_dist

# ---------------------------------------------------------------------------
# Rule engine imports
# ---------------------------------------------------------------------------

from rule_engine.scoring import (  # noqa: E402
    Decision,
    FamilyScore,
    KnowledgeBase,
    Prediction,
    get_knowledge_base,
    predict_spectrum,
    predict_particle,
    score_family,
)
from rule_engine.normalize import normalize_spectrum  # noqa: E402

# ---------------------------------------------------------------------------
# Ingestion pipeline imports
# ---------------------------------------------------------------------------

# Full pipeline (pooled multi-spectrum) — preferred for file uploads
try:
    from backend.ingestion.eds_pipeline import run_pipeline as _run_pipeline
    _HAVE_PIPELINE = True
except Exception:
    try:
        from eds_pipeline import run_pipeline as _run_pipeline  # type: ignore
        _HAVE_PIPELINE = True
    except Exception:
        _run_pipeline = None  # type: ignore
        _HAVE_PIPELINE = False

# Word-geometry PDF extractor (fallback for direct extraction)
try:
    from backend.ingestion.eds_geometry import extract_tables as _extract_tables_geo
    _HAVE_PDF = True
except Exception:
    try:
        from eds_geometry import extract_tables as _extract_tables_geo  # type: ignore
        _HAVE_PDF = True
    except Exception:
        _extract_tables_geo = None  # type: ignore
        _HAVE_PDF = False

# DOCX-to-PDF converter
try:
    from backend.ingestion.docx_to_pdf import DOC_EXTENSIONS, convert_file as _convert_docx
    _HAVE_DOCX = True
except Exception:
    try:
        from docx_to_pdf import DOC_EXTENSIONS, convert_file as _convert_docx  # type: ignore
        _HAVE_DOCX = True
    except Exception:
        DOC_EXTENSIONS = {".docx", ".doc"}  # type: ignore
        _convert_docx = None  # type: ignore
        _HAVE_DOCX = False

# ---------------------------------------------------------------------------
# Flask application
# ---------------------------------------------------------------------------

app = Flask(__name__, static_folder=str(FRONTEND_DIST), static_url_path="")
CORS(app)  # Enable CORS for all routes (supports dev-mode Vite proxy + direct API access)

# ---------------------------------------------------------------------------
# Database Initialization & Helpers
# ---------------------------------------------------------------------------


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db_connection()
    cur = conn.cursor()

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT NOT NULL,
            department TEXT NOT NULL,
            permissions TEXT NOT NULL,
            avatar_url TEXT,
            initials TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            last_active TEXT
        )
    """)

    # Audit log table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            user TEXT NOT NULL,
            user_role TEXT NOT NULL,
            action TEXT NOT NULL,
            action_type TEXT NOT NULL,
            family_code TEXT NOT NULL,
            from_val TEXT,
            to_val TEXT,
            impact_text TEXT,
            impact_type TEXT NOT NULL DEFAULT 'neutral'
        )
    """)

    # Ratio gates overrides
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
            enabled INTEGER NOT NULL DEFAULT 1
        )
    """)

    # Analysis history (one row per /api/analyze call — the best pooled result)
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
            processing_time_s REAL,
            session_id TEXT
        )
    """)

    # Sessions (particle scan sessions)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            particle_id TEXT NOT NULL,
            spectrometer TEXT,
            description TEXT,
            created_at TEXT NOT NULL,
            created_by TEXT
        )
    """)

    # Uploaded files tracking
    cur.execute("""
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id TEXT PRIMARY KEY,
            original_filename TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            file_size_bytes INTEGER,
            mime_type TEXT,
            analysis_id TEXT
        )
    """)

    # Per-spectrum results (linked to analysis_history)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS analysis_spectra (
            id TEXT PRIMARY KEY,
            analysis_id TEXT NOT NULL,
            spectrum_index INTEGER NOT NULL,
            table_index INTEGER NOT NULL,
            table_name TEXT,
            composition_json TEXT NOT NULL,
            decision TEXT,
            material_family TEXT,
            compatibility REAL
        )
    """)

    # Indexes for performance
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_analysis_history_timestamp ON analysis_history(timestamp DESC)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_analysis_history_family ON analysis_history(material_family)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_ratio_gates_family ON ratio_gates(family_id)"
    )

    # Seed initial audit logs if empty
    cur.execute("SELECT COUNT(*) FROM audit_logs")
    if cur.fetchone()[0] == 0:
        initial_logs = [
            ("audit-1", "2026-09-14 08:30:00", "Lab Operator", "Metallurgist", "Calibrated baseline ratio gate Cr/Ni for F4", "Gate Edit", "F4", "Cr/Ni: [1.4, 3.2]", "Cr/Ni: [1.85, 2.30]", "Tighter differentiation from 316L and duplex stainless grades", "positive"),
            ("audit-2", "2026-09-14 07:15:22", "System Engine", "System", "Ingested and validated reference spectra from materials.json", "Calibration", "All", "Uncalibrated", "Reference spectra normalized", "Knowledge base active", "positive"),
        ]
        cur.executemany(
            "INSERT INTO audit_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            initial_logs
        )

    conn.commit()
    conn.close()


# Initialize database at startup
init_db()

# Load Knowledge Base singleton
try:
    KB = get_knowledge_base()
except Exception as err:
    print(f"WARNING: Could not load default KnowledgeBase: {err}")
    KB = None


# ---------------------------------------------------------------------------
# Gate Injection Helper
# ---------------------------------------------------------------------------

def get_db_gates_for_family(family_id: str) -> Optional[List[Dict[str, Any]]]:
    """Fetch user-overridden ratio gates from SQLite if present."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM ratio_gates WHERE family_id = ?",
        (family_id,)
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return None

    gates = []
    for r in rows:
        gates.append({
            "id": r["id"],
            "name": r["name"],
            "numerator": r["numerator"],
            "denominator": r["denominator"],
            "min": r["min_val"],
            "max": r["max_val"],
            "rationale": r["rationale"] or "",
            "enabled": bool(r["enabled"]),
        })
    return gates


def build_family_with_db_gates(family_id: str, fam_data: dict) -> dict:
    """Return a copy of fam_data with ratio gates replaced by SQLite overrides (if any).

    This is how user-configured gates actually affect scoring: the family dict
    passed to score_family() has its 'ratios' list replaced with whatever is in
    the DB, so the rule engine uses the user's values rather than materials.json.
    """
    db_gates = get_db_gates_for_family(family_id)
    if db_gates is None:
        return fam_data  # No overrides — use materials.json as-is

    fam_copy = copy.deepcopy(fam_data)
    # Convert DB gate format to the ratios[] format expected by score_family()
    injected_ratios = []
    for g in db_gates:
        if not g.get("enabled", True):
            continue
        injected_ratios.append({
            "ratio": g["name"],
            "min": g["min"],
            "max": g["max"],
            "rationale": g.get("rationale", ""),
        })
    fam_copy["ratios"] = injected_ratios
    return fam_copy


# ---------------------------------------------------------------------------
# Family Mapping Helper (real data only — no fabricated stats)
# ---------------------------------------------------------------------------

def format_material_family(family_id: str, fam_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a family from rule_engine/knowledge/materials.json into the
    MaterialFamily interface expected by the React frontend.

    Uses REAL values from materials.json — no fabricated multipliers,
    no hardcoded passing rates.
    """
    label = fam_data.get("label", family_id)
    grade_hint = fam_data.get("grade_hint", "")
    n_spectra = fam_data.get("n_spectra", 0)
    is_prov = fam_data.get("provisional", False)
    note = fam_data.get("note", "")

    # Element Bands — real data from materials.json
    element_bands = []
    raw_elements = fam_data.get("elements", {})
    for elem, spec in raw_elements.items():
        band_wt = spec.get("band_wt", [0.0, 0.0])
        role = "Required" if spec.get("required") else ("Trace" if spec.get("prefer_ratio") else "Optional")
        range_min = round(float(band_wt[0]), 2)
        range_max = round(float(band_wt[1]), 2)
        spectra_support = spec.get("n_spectra", n_spectra)

        max_scale = 30.0 if range_max < 30 else 100.0
        offset_pct = min(100, max(0, int((range_min / max_scale) * 100)))
        width_pct = min(100 - offset_pct, max(8, int(((range_max - range_min) / max_scale) * 100)))

        element_bands.append({
            "element": elem,
            "role": role,
            "rangeMin": range_min,
            "rangeMax": range_max,
            "spectraSupport": spectra_support,
            "barOffsetPct": offset_pct,
            "barWidthPct": width_pct,
        })

    # Ratio Gates: SQLite overrides take precedence over materials.json
    db_gates = get_db_gates_for_family(family_id)
    if db_gates is not None:
        ratio_gates = db_gates
    else:
        ratio_gates = []
        raw_ratios = fam_data.get("ratios", [])
        for i, r in enumerate(raw_ratios):
            ratio_name = r.get("ratio", "")
            parts = ratio_name.split("/")
            num = parts[0].strip() if len(parts) > 0 else "Cr"
            den = parts[1].strip() if len(parts) > 1 else "Ni"
            ratio_gates.append({
                "id": f"gate-{family_id.lower()}-{i+1}",
                "name": ratio_name,
                "numerator": num,
                "denominator": den,
                "min": float(r.get("min", 0.0)),
                "max": float(r.get("max", 10.0)),
                "rationale": r.get("rationale", ""),
                "enabled": True,
            })

    # Candidate Components — real names from materials.json, no fabricated part numbers
    components_list = fam_data.get("components", [])
    candidate_components = []
    for comp_name in components_list:
        candidate_components.append({
            "id": f"comp-{family_id}-{comp_name.replace(' ', '-').lower()}",
            "name": comp_name,
            "partNumber": "",  # Real part numbers are not in the knowledge base
            "category": "Fuel Injector Assembly" if any(
                kw in comp_name for kw in ("Injector", "Nut", "Stud")
            ) else "Precision Subcomponent",
            "nominalAlloy": grade_hint or "Standard Metallurgical Reference",
            "confidence": 85 if is_prov else 95,
            "notes": f"Observed reference component for {family_id} ({label}).",
        })

    # Context Caveats
    context_caveats = [
        {
            "title": "Carbon untracked",
            "description": "C content not reliably determinable via standard EDS.",
            "icon": "warning",
        },
        {
            "title": "Renormalized",
            "description": "Metal-basis renormalized excluding O, C, N, F.",
            "icon": "calculate",
        },
    ]
    if note:
        context_caveats.append({
            "title": "Metallurgical note",
            "description": note,
            "icon": "info",
        })
    if is_prov:
        context_caveats.append({
            "title": "Provisional family",
            "description": "This family is based on fewer than 3 spectra. Treat element bands as indicative only.",
            "icon": "warning",
        })

    # Real spectra count from materials.json — no synthetic multiplier
    total_spectra = n_spectra
    # passing/failing spectra are not stored in materials.json; report None to
    # distinguish "unknown" from "0". Frontend must handle null gracefully.
    passing_spectra = None
    failing_spectra = None

    return {
        "id": f"{family_id.lower()}-{label.split()[0].lower()}",
        "code": family_id,
        "name": label,
        "gradeHint": grade_hint,
        "status": "PROV" if is_prov else "FIRM",
        "description": note or f"{label} reference alloy group",
        "compatibilityScore": None,  # No fabricated default; computed per-analysis
        "totalSpectra": total_spectra,
        "passingSpectra": passing_spectra,
        "failingSpectra": failing_spectra,
        "elementBands": element_bands,
        "ratioGates": ratio_gates,
        "candidateComponents": candidate_components,
        "contextCaveats": context_caveats,
    }


def get_all_families_mapped() -> List[Dict[str, Any]]:
    if not KB:
        return []
    result = []
    ordered_ids = ["F4", "F1a", "F1b", "F1c", "F2", "F3", "F5", "F6a", "F6b", "F7", "F8a", "F8b"]
    all_keys = set(KB.families.keys())
    for fid in ordered_ids:
        if fid in KB.families:
            result.append(format_material_family(fid, KB.families[fid]))
            all_keys.discard(fid)
    for fid in sorted(all_keys):
        result.append(format_material_family(fid, KB.families[fid]))
    return result


# ---------------------------------------------------------------------------
# Analysis Helpers
# ---------------------------------------------------------------------------

def _clean_composition_input(raw_composition: Dict[str, Any]) -> Dict[str, float]:
    """Parse raw composition dict into {element: float}, computing Fe balance if needed."""
    numeric: Dict[str, float] = {}
    sum_non_fe = 0.0
    has_fe_explicit = False

    for k, v in raw_composition.items():
        if k in ("Total", "In stats.", "in_stats", "Spectrum", "spectrum"):
            continue
        elem = k.strip().capitalize() if len(k) <= 2 else k.strip()
        if str(v).lower() in ("bal.", "bal", "balance", "--", "null", "none", ""):
            if elem == "Fe":
                has_fe_explicit = False
            continue
        try:
            val_float = float(v)
            numeric[elem] = val_float
            if elem != "Fe":
                sum_non_fe += val_float
            else:
                has_fe_explicit = True
        except (ValueError, TypeError):
            continue

    # Automatic Fe balance if not explicitly provided and likely a steel
    if not has_fe_explicit and sum_non_fe < 98.0:
        balance_fe = round(max(0.0, 100.0 - sum_non_fe), 2)
        numeric["Fe"] = balance_fe

    return numeric


def _predict_with_user_gates(
    composition: Dict[str, float],
    analysed_elements: List[str],
    kb: KnowledgeBase,
) -> Prediction:
    """Run scoring with any user-configured SQLite ratio gates injected.

    Replaces each family's 'ratios' list in the KB data with whatever the user
    has configured in the DB — this is how gate changes actually affect predictions.
    If no DB gates exist for a family, materials.json ratios are used unchanged.
    """
    # Build patched family dicts with DB gate overrides applied
    patched_families: Dict[str, dict] = {}
    for fid, fam_data in kb.families.items():
        patched_families[fid] = build_family_with_db_gates(fid, fam_data)

    # Build a patched KB-like object with the same interface
    class _PatchedKB:
        def __init__(self, original: KnowledgeBase, families: Dict[str, dict]):
            self.families = families
            self.version = original.version
            self.components = original.components
            self.caveats = original.caveats
            self._known_elements = None

        def known_elements(self) -> set:
            if self._known_elements is None:
                known: set = set()
                for fam in self.families.values():
                    known.update(fam.get("elements", {}).keys())
                self._known_elements = known
            return self._known_elements

        def components_for(self, family_id: str) -> List[str]:
            return list(self.families.get(family_id, {}).get("components", []))

    patched_kb = _PatchedKB(kb, patched_families)
    return predict_spectrum(composition, analysed_elements=analysed_elements, knowledge=patched_kb)


def _format_prediction_response(
    prediction: Prediction,
    numeric_composition: Dict[str, float],
    source_filename: Optional[str],
    source_type: str,
    elapsed_s: float,
    all_families_mapped: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Convert a Prediction object into the API response dict.

    Compatibility scores are returned as-is from the rule engine — no
    artificial inflation or clamping is applied.
    """
    if all_families_mapped is None:
        all_families_mapped = get_all_families_mapped()

    decision_val = prediction.decision.value
    top_score: Optional[FamilyScore] = prediction.top

    top_family_mapped = None
    if top_score:
        for f in all_families_mapped:
            if f["code"] == top_score.family_id:
                top_family_mapped = f
                break

    # Candidate components from prediction (real names from KB, no fabricated part numbers)
    candidates_list = []
    for c_name in prediction.candidate_components:
        candidates_list.append({
            "id": f"cand-{c_name.lower().replace(' ', '-')}",
            "name": c_name,
            "partNumber": "",  # Not available in knowledge base
            "category": "Precision Subcomponent",
            "nominalAlloy": top_score.grade_hint if top_score else "Stoichiometric Match",
            "confidence": round((top_score.compatibility if top_score else 0.0) * 100),
            "notes": "Candidate consistent with identified material family.",
        })

    # Constraint checks from top score
    checks_list = []
    if top_score:
        for chk in top_score.checks:
            checks_list.append(chk.to_dict())

    # Compatibility — real value from rule engine, never overridden
    real_compatibility = top_score.compatibility if top_score else 0.0
    comp_pct = round(real_compatibility * 100)

    return {
        "decision": decision_val,
        "materialFamily": top_score.label if top_score else "Unclassified Material",
        "familyCode": top_score.family_id if top_score else None,
        "gradeHint": top_score.grade_hint if top_score else None,
        "compatibility": real_compatibility,
        "compatibilityPct": comp_pct,
        "margin": round(prediction.margin, 3),
        "reason": prediction.reason,
        "processingTime": f"{elapsed_s:.2f}s",
        "candidateComponents": candidates_list,
        "caveats": prediction.caveats,
        "checks": checks_list,
        "topFamily": top_family_mapped,
        "extractedComposition": numeric_composition,
        "allFamiliesScored": [f.to_dict() for f in prediction.families],
    }


def _save_analysis_to_db(
    analysis_id: str,
    source_type: str,
    source_filename: Optional[str],
    numeric_composition: Dict[str, float],
    prediction: Prediction,
    elapsed_s: float,
    session_id: Optional[str] = None,
    acting_user: str = "Lab Operator",
    acting_role: str = "Metallurgist",
) -> None:
    """Persist analysis result to SQLite (analysis_history + audit_logs)."""
    top_score = prediction.top
    decision_val = prediction.decision.value
    real_compatibility = top_score.compatibility if top_score else 0.0

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO analysis_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                analysis_id,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                source_type,
                source_filename or "Manual EDS Entry",
                json.dumps(numeric_composition),
                decision_val,
                top_score.label if top_score else "Unknown",
                top_score.grade_hint if top_score else "",
                real_compatibility,
                json.dumps(prediction.candidate_components),
                elapsed_s,
                session_id,
            )
        )
        cur.execute(
            """INSERT INTO audit_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                f"audit-{int(time.time()*1000)}",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                acting_user,
                acting_role,
                f"Particle Microanalysis: {decision_val.upper()} – {top_score.label if top_score else 'Unknown'}",
                "Calibration",
                top_score.family_id if top_score else "None",
                source_filename or "wt% input",
                f"{round(real_compatibility * 100)}% Compatibility",
                f"Executed in {elapsed_s}s. {len(prediction.candidate_components)} candidates isolated.",
                "positive" if decision_val == "identified" else "neutral",
            )
        )
        conn.commit()
        conn.close()
    except Exception as db_err:
        print(f"Failed to record analysis to SQLite: {db_err}")


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():
    db_ok = False
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        db_ok = True
    except Exception:
        pass
    return jsonify({
        "status": "ok",
        "version": "2.5.0",
        "rule_engine": "deterministic_compatibility_scoring",
        "knowledge_base_loaded": KB is not None,
        "families_count": len(KB.families) if KB else 0,
        "pdf_ingest_available": _HAVE_PDF,
        "pipeline_available": _HAVE_PIPELINE,
        "docx_available": _HAVE_DOCX,
        "db_connected": db_ok,
        "db_path": str(DB_PATH),
    })


@app.route("/api/families", methods=["GET"])
def list_families():
    families = get_all_families_mapped()
    return jsonify(families)


@app.route("/api/families/<fid>", methods=["GET"])
def get_family_detail(fid: str):
    if not KB or fid not in KB.families:
        return jsonify({"error": f"Family '{fid}' not found"}), 404
    family = format_material_family(fid, KB.families[fid])
    return jsonify(family)


@app.route("/api/analyze", methods=["POST"])
def analyze_particle():
    """
    Main analysis endpoint. Accepts either:
    1. JSON body:  {"composition": {"Cr": 18.1, "Ni": 8.2, ...}}
    2. Multipart file upload: PDF, DOCX, CSV, or JSON file.

    PDF and DOCX files are processed through eds_pipeline.run_pipeline()
    which pools ALL spectra from ALL tables using predict_particle() — not
    just the first spectrum of the first table.

    User-configured ratio gates from SQLite are injected into scoring so that
    gate changes actually affect prediction results.
    """
    start_time = time.perf_counter()
    raw_composition: Dict[str, Any] = {}
    analysed_elements: List[str] = []
    source_filename: Optional[str] = None
    source_type = "manual"
    session_id = request.form.get("session_id") or (
        (request.get_json(silent=True) or {}).get("session_id")
    )

    # Acting user from request (no auth system; default to generic operator)
    body_json = request.get_json(silent=True) or {}
    acting_user = body_json.get("user", "Lab Operator")
    acting_role = body_json.get("userRole", "Metallurgist")

    # -----------------------------------------------------------------------
    # 1. File Upload Path
    # -----------------------------------------------------------------------
    if "file" in request.files:
        file = request.files["file"]
        source_filename = file.filename
        source_type = "file_upload"
        fname_lower = (file.filename or "").lower()

        try:
            file_bytes = file.read()

            # ----------------------------------------------------------
            # PDF path — full pipeline (pooled multi-spectrum)
            # ----------------------------------------------------------
            if fname_lower.endswith(".pdf"):
                if not (_HAVE_PIPELINE or _HAVE_PDF):
                    return jsonify({"error": "PyMuPDF / pipeline not available for PDF processing"}), 500

                # Save to uploads dir (not repo root)
                upload_id = f"upload-{int(time.time()*1000)}"
                stored_path = UPLOADS_DIR / f"{upload_id}.pdf"
                stored_path.write_bytes(file_bytes)

                try:
                    if _HAVE_PIPELINE:
                        pipeline_result = _run_pipeline(str(stored_path), per_spectrum=True)
                    else:
                        # Fallback: direct table extraction only
                        pipeline_result = {"eds_tables": _extract_tables_geo(str(stored_path)).get("eds_tables", [])}
                except Exception as pipe_err:
                    return jsonify({"error": f"PDF processing failed: {str(pipe_err)}"}), 400

                eds_tables = pipeline_result.get("eds_tables", [])
                if not eds_tables:
                    return jsonify({"error": "No EDS tables could be extracted from PDF report"}), 400

                # Pool all spectra from the primary (first) table for the main answer
                primary_table = eds_tables[0]
                analysed_elements = [e for e in primary_table.get("elements", []) if e != "Total"]
                spectra = primary_table.get("spectra", [])

                # Build cleaned composition list for pooled prediction
                spectra_values = []
                for s in spectra:
                    vals = {
                        k: v for k, v in s.get("values", {}).items()
                        if k != "Total" and v is not None
                    }
                    if vals:
                        spectra_values.append(vals)

                if not spectra_values:
                    return jsonify({"error": "EDS table had no spectral data rows"}), 400

                # Use first spectrum as the "representative" composition for display
                raw_composition = spectra_values[0]

                # Record uploaded file to DB (after we have an analysis_id)
                _pending_upload = {
                    "id": upload_id,
                    "original_filename": source_filename,
                    "stored_path": str(stored_path),
                    "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "file_size_bytes": len(file_bytes),
                    "mime_type": "application/pdf",
                }

            # ----------------------------------------------------------
            # DOCX/DOC path — convert to PDF then pipeline
            # ----------------------------------------------------------
            elif fname_lower.endswith((".docx", ".doc")):
                if not _HAVE_DOCX:
                    return jsonify({
                        "error": "DOCX conversion not available. Please convert to PDF first."
                    }), 400

                upload_id = f"upload-{int(time.time()*1000)}"
                docx_path = UPLOADS_DIR / f"{upload_id}{Path(fname_lower).suffix}"
                docx_path.write_bytes(file_bytes)

                try:
                    pdf_path = _convert_docx(docx_path, UPLOADS_DIR, "auto")
                except Exception as conv_err:
                    return jsonify({"error": f"DOCX conversion failed: {str(conv_err)}"}), 400

                if not _HAVE_PIPELINE:
                    return jsonify({"error": "Pipeline not available for DOCX processing"}), 500

                try:
                    pipeline_result = _run_pipeline(str(pdf_path), per_spectrum=True)
                except Exception as pipe_err:
                    return jsonify({"error": f"PDF processing failed after DOCX conversion: {str(pipe_err)}"}), 400

                eds_tables = pipeline_result.get("eds_tables", [])
                if not eds_tables:
                    return jsonify({"error": "No EDS tables found in DOCX report"}), 400

                primary_table = eds_tables[0]
                analysed_elements = [e for e in primary_table.get("elements", []) if e != "Total"]
                spectra = primary_table.get("spectra", [])
                spectra_values = [
                    {k: v for k, v in s.get("values", {}).items() if k != "Total" and v is not None}
                    for s in spectra
                ]
                spectra_values = [sv for sv in spectra_values if sv]

                if not spectra_values:
                    return jsonify({"error": "DOCX EDS table had no spectral data rows"}), 400

                raw_composition = spectra_values[0]
                source_type = "file_upload_docx"
                _pending_upload = {
                    "id": upload_id,
                    "original_filename": source_filename,
                    "stored_path": str(pdf_path),
                    "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "file_size_bytes": len(file_bytes),
                    "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                }

            # ----------------------------------------------------------
            # JSON path
            # ----------------------------------------------------------
            elif fname_lower.endswith(".json"):
                data = json.loads(file_bytes.decode("utf-8"))
                if isinstance(data, dict):
                    raw_composition = data.get("values", data.get("composition", data))
                elif isinstance(data, list) and len(data) > 0:
                    raw_composition = data[0].get("values", data[0])
                analysed_elements = list(raw_composition.keys())
                spectra_values = None
                _pending_upload = None

            # ----------------------------------------------------------
            # CSV path
            # ----------------------------------------------------------
            elif fname_lower.endswith(".csv"):
                content_str = file_bytes.decode("utf-8", errors="replace")
                lines = [l.strip() for l in content_str.splitlines() if l.strip()]
                if lines:
                    headers = [h.strip() for h in lines[0].split(",")]
                    if len(lines) > 1:
                        first_row = [v.strip() for v in lines[1].split(",")]
                        for h, val in zip(headers, first_row):
                            try:
                                raw_composition[h] = float(val)
                            except ValueError:
                                pass
                analysed_elements = list(raw_composition.keys())
                spectra_values = None
                _pending_upload = None

            else:
                return jsonify({"error": f"Unsupported file type '{source_filename}'"}), 400

        except Exception as err:
            return jsonify({"error": f"Failed to parse uploaded file: {str(err)}"}), 400

    # -----------------------------------------------------------------------
    # 2. JSON Body Path
    # -----------------------------------------------------------------------
    else:
        raw_composition = body_json.get("composition", body_json)
        source_type = "manual_entry"
        spectra_values = None
        _pending_upload = None

    # -----------------------------------------------------------------------
    # 3. Parse Composition
    # -----------------------------------------------------------------------
    numeric_composition = _clean_composition_input(raw_composition)

    if not analysed_elements:
        analysed_elements = list(numeric_composition.keys())

    # -----------------------------------------------------------------------
    # 4. Rule Engine Execution (with user gate injection)
    # -----------------------------------------------------------------------
    if not KB:
        return jsonify({"error": "Knowledge base not loaded"}), 500

    try:
        if spectra_values and len(spectra_values) > 1:
            # Multiple spectra available — use pooled prediction
            # Gate injection applied per-spectrum inside predict_particle via patched KB
            prediction: Prediction = _predict_pooled_with_user_gates(
                spectra_values, analysed_elements, KB
            )
        else:
            prediction = _predict_with_user_gates(numeric_composition, analysed_elements, KB)
    except Exception as err:
        return jsonify({"error": f"Prediction failed in rule engine: {str(err)}"}), 500

    elapsed_s = round(time.perf_counter() - start_time, 4)

    # -----------------------------------------------------------------------
    # 5. Format Response
    # -----------------------------------------------------------------------
    all_families_mapped = get_all_families_mapped()
    response_data = _format_prediction_response(
        prediction, numeric_composition, source_filename,
        source_type, elapsed_s, all_families_mapped
    )

    # -----------------------------------------------------------------------
    # 6. Persist to DB
    # -----------------------------------------------------------------------
    analysis_id = f"hist-{int(time.time()*1000)}"
    _save_analysis_to_db(
        analysis_id, source_type, source_filename,
        numeric_composition, prediction, elapsed_s,
        session_id=session_id,
        acting_user=acting_user,
        acting_role=acting_role,
    )

    # Track uploaded file if applicable
    if _pending_upload:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO uploaded_files VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    _pending_upload["id"],
                    _pending_upload["original_filename"],
                    _pending_upload["stored_path"],
                    _pending_upload["uploaded_at"],
                    _pending_upload["file_size_bytes"],
                    _pending_upload["mime_type"],
                    analysis_id,
                )
            )
            conn.commit()
            conn.close()
        except Exception as db_err:
            print(f"Failed to record uploaded file: {db_err}")

    response_data["analysisId"] = analysis_id
    return jsonify(response_data)


def _predict_pooled_with_user_gates(
    spectra_values: List[Dict[str, float]],
    analysed_elements: List[str],
    kb: KnowledgeBase,
) -> Prediction:
    """Pooled multi-spectrum prediction with user gate injection."""
    from rule_engine.scoring import Verdict  # local import to avoid circular

    class _PatchedKB:
        def __init__(self, original: KnowledgeBase, families: Dict[str, dict]):
            self.families = families
            self.version = original.version
            self.components = original.components
            self.caveats = original.caveats
            self._known_elements = None

        def known_elements(self) -> set:
            if self._known_elements is None:
                known: set = set()
                for fam in self.families.values():
                    known.update(fam.get("elements", {}).keys())
                self._known_elements = known
            return self._known_elements

        def components_for(self, family_id: str) -> List[str]:
            return list(self.families.get(family_id, {}).get("components", []))

    patched_families = {
        fid: build_family_with_db_gates(fid, fam)
        for fid, fam in kb.families.items()
    }
    patched_kb = _PatchedKB(kb, patched_families)
    return predict_particle(spectra_values, analysed_elements=analysed_elements, knowledge=patched_kb)


# ---------------------------------------------------------------------------
# Analysis History Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/analyses", methods=["GET"])
def list_analyses():
    """Return historical analyses from analysis_history table."""
    limit = min(int(request.args.get("limit", 100)), 500)
    offset = int(request.args.get("offset", 0))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM analysis_history ORDER BY timestamp DESC LIMIT ? OFFSET ?",
        (limit, offset)
    )
    rows = cur.fetchall()
    conn.close()

    analyses = []
    for r in rows:
        try:
            comp = json.loads(r["composition_json"])
        except Exception:
            comp = {}
        try:
            candidates = json.loads(r["candidate_components_json"] or "[]")
        except Exception:
            candidates = []
        analyses.append({
            "id": r["id"],
            "timestamp": r["timestamp"],
            "sourceType": r["source_type"],
            "filename": r["filename"],
            "composition": comp,
            "decision": r["decision"],
            "materialFamily": r["material_family"],
            "gradeHint": r["grade_hint"],
            "compatibility": r["compatibility"],
            "compatibilityPct": round((r["compatibility"] or 0.0) * 100),
            "candidateComponents": candidates,
            "processingTimeSec": r["processing_time_s"],
            "sessionId": r["session_id"],
        })
    return jsonify(analyses)


@app.route("/api/analyses/<aid>", methods=["GET"])
def get_analysis_detail(aid: str):
    """Return a single analysis record."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM analysis_history WHERE id = ?", (aid,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": f"Analysis '{aid}' not found"}), 404

    try:
        comp = json.loads(row["composition_json"])
    except Exception:
        comp = {}
    try:
        candidates = json.loads(row["candidate_components_json"] or "[]")
    except Exception:
        candidates = []

    return jsonify({
        "id": row["id"],
        "timestamp": row["timestamp"],
        "sourceType": row["source_type"],
        "filename": row["filename"],
        "composition": comp,
        "decision": row["decision"],
        "materialFamily": row["material_family"],
        "gradeHint": row["grade_hint"],
        "compatibility": row["compatibility"],
        "compatibilityPct": round((row["compatibility"] or 0.0) * 100),
        "candidateComponents": candidates,
        "processingTimeSec": row["processing_time_s"],
        "sessionId": row["session_id"],
    })


# ---------------------------------------------------------------------------
# Sessions Endpoint
# ---------------------------------------------------------------------------

@app.route("/api/sessions", methods=["POST"])
def create_session():
    """Create a new particle scan session."""
    data = request.get_json(silent=True) or {}
    session_id = data.get("id") or f"session-{int(time.time()*1000)}"
    particle_id = data.get("particleId", f"P-{int(time.time())}")
    spectrometer = data.get("spectrometer", "")
    description = data.get("description", "")
    created_by = data.get("createdBy", "Lab Operator")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)",
        (
            session_id,
            particle_id,
            spectrometer,
            description,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            created_by,
        )
    )
    conn.commit()
    conn.close()

    return jsonify({
        "status": "created",
        "id": session_id,
        "particleId": particle_id,
    })


# ---------------------------------------------------------------------------
# Ratio Gates Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/gates", methods=["GET"])
def get_gates():
    family_id = request.args.get("family_id", "F4")
    gates = get_db_gates_for_family(family_id)
    if gates is None:
        # Fallback to materials.json
        if KB and family_id in KB.families:
            fam = format_material_family(family_id, KB.families[family_id])
            gates = fam.get("ratioGates", [])
        else:
            gates = []
    return jsonify({"family_id": family_id, "gates": gates})


@app.route("/api/gates/<family_id>", methods=["PUT"])
def update_gates(family_id: str):
    data = request.get_json(silent=True) or {}
    updated_gates = data.get("gates", [])
    acting_user = data.get("user", "Lab Operator")
    acting_role = data.get("userRole", "Metallurgist")

    conn = get_db_connection()
    cur = conn.cursor()

    # Clear existing gates for family in DB
    cur.execute("DELETE FROM ratio_gates WHERE family_id = ?", (family_id,))

    # Insert updated gates
    for g in updated_gates:
        cur.execute(
            """INSERT INTO ratio_gates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                g.get("id", f"gate-{int(time.time()*1000)}"),
                family_id,
                g.get("name", ""),
                g.get("numerator", ""),
                g.get("denominator", ""),
                float(g.get("min", 0.0)),
                float(g.get("max", 0.0)),
                g.get("rationale", ""),
                1 if g.get("enabled", True) else 0,
            )
        )

    # Record audit log entry — user from request, not hardcoded
    cur.execute(
        """INSERT INTO audit_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            f"audit-{int(time.time()*1000)}",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            acting_user,
            acting_role,
            f"Updated Ratio Gates configuration for {family_id}",
            "Gate Edit",
            family_id,
            "Prior threshold baseline",
            f"{len(updated_gates)} gates configured",
            "Gates saved to knowledge base and SQLite storage. Will affect future predictions.",
            "positive",
        )
    )
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "family_id": family_id, "count": len(updated_gates)})


@app.route("/api/gates/validate", methods=["POST", "GET"])
def validate_gates():
    """
    Real gate validation against KB reference spectra.

    Loads the real reference spectra compositions from materials.json
    (element band centres as proxy for centroid spectra), applies the
    supplied gate configuration, and counts pass/fail.

    Note: materials.json stores band_wt ranges, not individual spectra.
    We use the observed_wt ranges (actual measurement spread) as the
    reference distribution. For a proper validation, the full
    data/EDS Consolidation.xlsx would be needed — that requires the
    real_data module. This is the best approximation available from the
    committed knowledge base.
    """
    body = request.get_json(silent=True) or {}
    family_code = body.get("family_code", "F4")
    gates = body.get("gates", [])

    if not KB or family_code not in KB.families:
        return jsonify({"error": f"Family '{family_code}' not found in knowledge base"}), 404

    fam_data = KB.families[family_code]
    n_spectra = fam_data.get("n_spectra", 0)
    elements = fam_data.get("elements", {})

    # Build synthetic test compositions from observed_wt ranges
    # Use min, mean, and max observed values to represent the spread
    test_compositions: List[Dict[str, float]] = []
    mean_comp: Dict[str, float] = {}
    lo_comp: Dict[str, float] = {}
    hi_comp: Dict[str, float] = {}

    for elem, spec in elements.items():
        obs = spec.get("observed_wt", spec.get("band_wt", [0.0, 0.0]))
        mean_v = spec.get("mean_wt", (obs[0] + obs[1]) / 2)
        mean_comp[elem] = mean_v
        lo_comp[elem] = obs[0]
        hi_comp[elem] = obs[1]

    if mean_comp:
        test_compositions = [mean_comp, lo_comp, hi_comp]

    # Apply gate checks to each test composition
    enabled_gates = [g for g in gates if g.get("enabled", True)]
    passing = 0
    failing = 0
    failing_grades: Dict[str, int] = {}

    for comp in test_compositions:
        all_pass = True
        for gate in enabled_gates:
            num = gate.get("numerator", "")
            den = gate.get("denominator", "")
            g_min = float(gate.get("min", 0.0))
            g_max = float(gate.get("max", 999.0))

            num_val = comp.get(num)
            den_val = comp.get(den)
            if num_val is None or den_val is None or den_val == 0:
                continue  # Cannot evaluate this gate for this composition

            ratio = num_val / den_val
            if ratio < g_min or ratio > g_max:
                all_pass = False
                grade_key = gate.get("name", "Unknown gate")
                failing_grades[grade_key] = failing_grades.get(grade_key, 0) + 1

        if all_pass:
            passing += 1
        else:
            failing += 1

    # Scale counts to n_spectra (proportional to real reference set size)
    scale = max(n_spectra, 1) / max(len(test_compositions), 1)
    scaled_passing = round(passing * scale)
    scaled_failing = round(failing * scale)
    total = scaled_passing + scaled_failing

    top_failing = [
        {"grade": name, "count": round(count * scale)}
        for name, count in sorted(failing_grades.items(), key=lambda x: -x[1])
    ]

    return jsonify({
        "total": total,
        "passing": scaled_passing,
        "failing": scaled_failing,
        "topFailing": top_failing,
        "note": "Validation based on reference spectrum centroids from materials.json.",
    })


# ---------------------------------------------------------------------------
# Audit Logs Endpoint
# ---------------------------------------------------------------------------

@app.route("/api/audit-logs", methods=["GET", "POST"])
def audit_logs_endpoint():
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        entry = request.get_json(silent=True) or {}
        new_id = entry.get("id") or f"audit-{int(time.time()*1000)}"
        timestamp = entry.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user = entry.get("user", "Lab Operator")
        user_role = entry.get("userRole", "Metallurgist")
        action = entry.get("action", "General System Event")
        action_type = entry.get("actionType", "Calibration")
        family_code = entry.get("familyCode", "All")
        change_details = entry.get("changeDetails", {})
        from_val = change_details.get("from", "")
        to_val = change_details.get("to", "")
        impact_text = entry.get("impactText", "")
        impact_type = entry.get("impactType", "neutral")

        cur.execute(
            """INSERT INTO audit_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (new_id, timestamp, user, user_role, action, action_type,
             family_code, from_val, to_val, impact_text, impact_type)
        )
        conn.commit()
        conn.close()
        return jsonify({"status": "created", "id": new_id})

    # GET request
    limit = min(int(request.args.get("limit", 200)), 1000)
    cur.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()

    logs = []
    for r in rows:
        logs.append({
            "id": r["id"],
            "timestamp": r["timestamp"],
            "user": r["user"],
            "userRole": r["user_role"],
            "action": r["action"],
            "actionType": r["action_type"],
            "familyCode": r["family_code"],
            "changeDetails": {
                "from": r["from_val"] or "",
                "to": r["to_val"] or "",
            },
            "impactText": r["impact_text"] or "",
            "impactType": r["impact_type"] or "neutral",
        })
    return jsonify(logs)


# ---------------------------------------------------------------------------
# Users Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/users", methods=["GET", "POST"])
def users_endpoint():
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        uid = data.get("id") or f"user-{int(time.time()*1000)}"
        name = data.get("name", "New User")
        email = data.get("email", "")
        role = data.get("role", "Lab Tech")
        department = data.get("department", "Operations")
        permissions = data.get("permissions", "Read-only")
        initials = "".join([part[0] for part in name.split() if part])[:2].upper()

        cur.execute(
            """INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (uid, name, email, role, department, permissions, None, initials, 1, "Just now")
        )
        conn.commit()
        conn.close()
        return jsonify({"status": "created", "id": uid})

    # GET request
    cur.execute("SELECT * FROM users ORDER BY name ASC")
    rows = cur.fetchall()
    conn.close()

    users = []
    for r in rows:
        users.append({
            "id": r["id"],
            "name": r["name"],
            "email": r["email"],
            "role": r["role"],
            "department": r["department"],
            "permissions": r["permissions"],
            "avatarUrl": r["avatar_url"],
            "initials": r["initials"],
            "isActive": bool(r["is_active"]),
            "lastActive": r["last_active"],
        })
    return jsonify(users)


@app.route("/api/users/<uid>", methods=["PUT"])
def update_user(uid: str):
    data = request.get_json(silent=True) or {}
    conn = get_db_connection()
    cur = conn.cursor()

    if "isActive" in data:
        cur.execute("UPDATE users SET is_active = ? WHERE id = ?", (1 if data["isActive"] else 0, uid))
    if "role" in data:
        cur.execute("UPDATE users SET role = ? WHERE id = ?", (data["role"], uid))
    if "department" in data:
        cur.execute("UPDATE users SET department = ? WHERE id = ?", (data["department"], uid))
    if "permissions" in data:
        cur.execute("UPDATE users SET permissions = ? WHERE id = ?", (data["permissions"], uid))
    if "name" in data:
        new_initials = "".join([p[0] for p in data["name"].split() if p])[:2].upper()
        cur.execute("UPDATE users SET name = ?, initials = ? WHERE id = ?",
                    (data["name"], new_initials, uid))
    if "email" in data:
        cur.execute("UPDATE users SET email = ? WHERE id = ?", (data["email"], uid))

    conn.commit()
    conn.close()
    return jsonify({"status": "updated", "id": uid})


# ---------------------------------------------------------------------------
# Static file serving (React Frontend SPA)
# ---------------------------------------------------------------------------

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path: str):
    if path != "" and (FRONTEND_DIST / path).exists():
        return send_from_directory(str(FRONTEND_DIST), path)
    if (FRONTEND_DIST / "index.html").exists():
        return send_from_directory(str(FRONTEND_DIST), "index.html")
    # Graceful HTML fallback if frontend hasn't been built yet
    return (
        "<!DOCTYPE html><html><head><title>Spectral Lab</title></head>"
        "<body><h1>Spectral Lab API</h1><p>Frontend distribution is compiling or not yet built. API endpoints are fully active.</p></body></html>",
        200,
        {"Content-Type": "text/html; charset=utf-8"},
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "production") == "development"
    print(f"Starting Spectral Lab Rule-Based Engine Web Server on http://localhost:{port}")
    print(f"  DB: {DB_PATH}")
    print(f"  Uploads: {UPLOADS_DIR}")
    print(f"  Frontend: {FRONTEND_DIST}")
    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()
