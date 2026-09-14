"""
backend/kb_service.py
======================
Bridges the Spectral-Lab frontend's MaterialFamily data model to the real
knowledge base that drives prediction: eds_core/rule_engine/knowledge/materials.json.

Every read the UI shows and every write the Knowledge Base Editor makes goes
through this module, so "the displayed data actually drives the Rule Engine"
(requirement 5) instead of a second, disconnected copy of the data.

No ML. This module and everything it touches (rule_engine.scoring) is pure
stdlib deterministic scoring - see eds_core/docs/EDS_AUDIT.md.
"""

from __future__ import annotations

import json
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.paths import KNOWLEDGE_PATH, KNOWLEDGE_BACKUP_DIR

_LOCK = threading.Lock()


class KBValidationError(Exception):
    def __init__(self, issues: List[str], warnings: Optional[List[str]] = None):
        self.issues = issues
        self.warnings = warnings or []
        super().__init__("; ".join(issues))


class KBNotFoundError(Exception):
    pass


# ---------------------------------------------------------------------------
# Raw load / save (the actual materials.json the rule engine reads)
# ---------------------------------------------------------------------------

def _read_raw() -> Dict[str, Any]:
    if not KNOWLEDGE_PATH.exists():
        raise KBNotFoundError(f"Knowledge base not found at {KNOWLEDGE_PATH}")
    with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_raw(data: Dict[str, Any]) -> None:
    # Validate structure using the project's own validator before anything
    # touches disk - a bad save must never reach the file the rule engine
    # loads at runtime.
    from rule_engine.validator import validate_knowledge_base

    report = validate_knowledge_base(data)
    if not report["is_valid"]:
        raise KBValidationError(report["issues"], report.get("warnings", []))

    KNOWLEDGE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if KNOWLEDGE_PATH.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        shutil.copy2(KNOWLEDGE_PATH, KNOWLEDGE_BACKUP_DIR / f"materials.{stamp}.json")

    tmp_path = KNOWLEDGE_PATH.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp_path.replace(KNOWLEDGE_PATH)

    # The rule engine (rule_engine.scoring) caches a singleton KnowledgeBase.
    # Force it to reload on the next prediction so edits take effect
    # immediately, without restarting the server.
    import rule_engine.scoring as scoring_mod

    scoring_mod._KB = None


# ---------------------------------------------------------------------------
# Transform: materials.json family dict  <->  frontend MaterialFamily shape
# ---------------------------------------------------------------------------

def _role_for(element: str, spec: Dict[str, Any]) -> str:
    if spec.get("required"):
        return "Required"
    if spec.get("prefer_ratio"):
        return "Trace"
    return "Optional"


def _element_band_to_frontend(element: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    band = spec.get("band_wt", [0.0, 0.0])
    lo, hi = (band + [0.0, 0.0])[:2] if len(band) < 2 else band
    lo = float(lo)
    hi = float(hi)
    # Bars are drawn on a 0-100 wt% canvas; clip so a >100 band (data error)
    # never breaks the layout.
    off = max(0.0, min(100.0, lo))
    width = max(0.5, min(100.0 - off, hi - lo))
    return {
        "element": element,
        "role": _role_for(element, spec),
        "rangeMin": round(lo, 3),
        "rangeMax": round(hi, 3),
        "spectraSupport": int(spec.get("n_spectra", 0)),
        "barOffsetPct": round(off, 2),
        "barWidthPct": round(width, 2),
        "provisional": bool(spec.get("provisional", False)),
        "preferRatio": bool(spec.get("prefer_ratio", False)),
    }


def _ratio_to_frontend(family_id: str, idx: int, ratio: Dict[str, Any]) -> Dict[str, Any]:
    name = ratio.get("ratio", "")
    num, _, den = name.partition("/")
    return {
        "id": f"{family_id}-ratio-{idx}",
        "name": name,
        "numerator": num.strip(),
        "denominator": den.strip(),
        "min": ratio.get("min", 0.0),
        "max": ratio.get("max", 0.0),
        "rationale": ratio.get("rationale", ""),
        "enabled": True,
    }


def _component_to_frontend(family_id: str, idx: int, name: str, component_meta: Dict[str, Any]) -> Dict[str, Any]:
    families_sharing = component_meta.get("families", []) if component_meta else []
    return {
        "id": f"{family_id}-comp-{idx}",
        "name": name,
        "partNumber": "—",
        "category": "; ".join(families_sharing) if families_sharing else family_id,
        "nominalAlloy": "",
        "confidence": 0,
        "notes": "Ambiguous across families" if component_meta and component_meta.get("ambiguous") else "",
    }


def family_to_frontend(family_id: str, family: Dict[str, Any], components_index: Dict[str, Any]) -> Dict[str, Any]:
    elements = family.get("elements", {})
    n_spectra = int(family.get("n_spectra", 0))
    provisional = bool(family.get("provisional", False))

    caveats = []
    if family.get("note"):
        caveats.append({"title": "Note", "description": family["note"], "icon": "info"})
    if provisional:
        caveats.append({
            "title": "Provisional family",
            "description": "Rests on limited reference data (<3 spectra); treat bands as indicative.",
            "icon": "warning",
        })
    for surf in family.get("surface_variants", []) or []:
        caveats.append({"title": "Surface variant", "description": str(surf), "icon": "layers"})

    return {
        "id": family_id,
        "code": family_id,
        "name": family.get("label", family_id),
        "gradeHint": family.get("grade_hint", ""),
        "status": "PROV" if provisional else "FIRM",
        "description": ", ".join(family.get("discriminators", [])) or family.get("label", ""),
        # Informational library-strength indicator (NOT a live prediction
        # score - real Rule-Based Score only exists per analysis, see
        # /api/analyze). Derived from how much reference data backs this
        # family so the KB browser isn't showing a meaningless 0.
        "compatibilityScore": min(97, 40 + n_spectra * 6),
        "totalSpectra": n_spectra,
        "passingSpectra": n_spectra,
        "failingSpectra": 0,
        "elementBands": [_element_band_to_frontend(el, spec) for el, spec in sorted(elements.items())],
        "ratioGates": [_ratio_to_frontend(family_id, i, r) for i, r in enumerate(family.get("ratios", []))],
        "candidateComponents": [
            _component_to_frontend(family_id, i, name, components_index.get(name, {}))
            for i, name in enumerate(family.get("components", []))
        ],
        "contextCaveats": caveats,
    }


def load_frontend_families() -> Dict[str, Any]:
    """Everything the Knowledge Base screen needs, transformed for the UI."""
    data = _read_raw()
    families = data.get("families", {})
    components = data.get("components", {})
    return {
        "version": data.get("version", "unknown"),
        "caveats": data.get("caveats", []),
        "unassignedComponents": data.get("unassigned_spectra_components", []),
        "families": [family_to_frontend(fid, fam, components) for fid, fam in sorted(families.items())],
    }


# ---------------------------------------------------------------------------
# Frontend edit payload -> materials.json family dict
# ---------------------------------------------------------------------------

def _frontend_band_to_element(band: Dict[str, Any]) -> Dict[str, Any]:
    lo = float(band.get("rangeMin", 0.0))
    hi = float(band.get("rangeMax", 0.0))
    role = band.get("role", "Optional")
    return {
        "band_wt": [lo, hi],
        "observed_wt": [lo, hi],
        "mean_wt": round((lo + hi) / 2, 4),
        "sigma_at_mean": max(0.01, round((hi - lo) / 4, 4)),
        "n_spectra": int(band.get("spectraSupport", 0)) or 1,
        "required": role == "Required",
        "provisional": bool(band.get("provisional", False)),
        "prefer_ratio": role == "Trace" or bool(band.get("preferRatio", False)),
    }


def _frontend_gate_to_ratio(gate: Dict[str, Any]) -> Dict[str, Any]:
    num = gate.get("numerator", "")
    den = gate.get("denominator", "")
    return {
        "ratio": gate.get("name") or f"{num}/{den}",
        "min": gate.get("min", 0.0),
        "max": gate.get("max", 0.0),
        "rationale": gate.get("rationale", ""),
    }


def frontend_to_family(payload: Dict[str, Any]) -> Dict[str, Any]:
    elements = {
        b["element"]: _frontend_band_to_element(b)
        for b in payload.get("elementBands", [])
        if b.get("element")
    }
    discriminators = [
        el for el, band in zip(
            [b.get("element") for b in payload.get("elementBands", [])],
            payload.get("elementBands", []),
        )
        if band.get("role") == "Required"
    ]
    components = [c.get("name") for c in payload.get("candidateComponents", []) if c.get("name")]
    return {
        "label": payload.get("name", payload.get("code", "Unnamed family")),
        "grade_hint": payload.get("gradeHint", ""),
        "discriminators": discriminators,
        "note": (payload.get("description") or ""),
        "ratios": [_frontend_gate_to_ratio(g) for g in payload.get("ratioGates", [])],
        "n_spectra": int(payload.get("totalSpectra", 0)),
        "n_components": len(components),
        "components": components,
        "surface_variants": [],
        "elements": elements,
        "provisional": payload.get("status", "FIRM") == "PROV",
    }


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def list_families() -> Dict[str, Any]:
    return load_frontend_families()


def create_family(family_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    with _LOCK:
        data = _read_raw()
        if family_id in data.setdefault("families", {}):
            raise ValueError(f"Family id '{family_id}' already exists")
        data["families"][family_id] = frontend_to_family(payload)
        _write_raw(data)
    return load_frontend_families()


def update_family(family_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    with _LOCK:
        data = _read_raw()
        if family_id not in data.get("families", {}):
            raise KBNotFoundError(f"Family id '{family_id}' not found")
        data["families"][family_id] = frontend_to_family(payload)
        _write_raw(data)
    return load_frontend_families()


def delete_family(family_id: str) -> Dict[str, Any]:
    with _LOCK:
        data = _read_raw()
        if family_id not in data.get("families", {}):
            raise KBNotFoundError(f"Family id '{family_id}' not found")
        del data["families"][family_id]
        _write_raw(data)
    return load_frontend_families()


def validate_payload(payload: Dict[str, Any], family_id: str = "DRAFT") -> Dict[str, Any]:
    """Dry-run validation for the editor's Save button, without writing."""
    from rule_engine.validator import validate_knowledge_base

    data = _read_raw()
    draft = dict(data)
    draft_families = dict(data.get("families", {}))
    draft_families[family_id] = frontend_to_family(payload)
    draft["families"] = draft_families
    return validate_knowledge_base(draft)
