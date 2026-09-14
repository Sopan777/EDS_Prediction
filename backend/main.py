"""
backend/main.py
================
Spectral-Lab MaterialID web backend.

    PDF upload --> eds_pipeline (extraction + normalization)
               --> rule_engine.scoring (Rule-Based Engine, driven by the
                   Knowledge Base at eds_core/rule_engine/knowledge/materials.json)
               --> JSON result for the Spectral-Lab Analyzer screen

Also exposes the Knowledge Base for browsing/editing (Knowledge Base Editor)
and a persisted Audit Log. No ML model is loaded or callable from this
service - see analyze_service.py's module docstring.

Run:
    uvicorn backend.main:app --reload --port 8000
(from the project root, so the "backend" package and "eds_core" import path
resolve correctly.)
"""

from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend import audit, kb_service
from backend.analyze_service import analyze_manual, analyze_pdf
from backend.paths import FRONTEND_DIST_DIR, SAMPLES_DIR, UPLOADS_DIR

app = FastAPI(title="Spectral-Lab MaterialID API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_UPLOAD_SUFFIXES = {".pdf", ".docx", ".doc"}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ManualAnalyzeRequest(BaseModel):
    elements: Dict[str, Any] = Field(..., description="element symbol -> wt%")
    analysedElements: Optional[List[str]] = None


class ElementBandIn(BaseModel):
    element: str
    role: str = "Optional"
    rangeMin: float = 0.0
    rangeMax: float = 0.0
    spectraSupport: int = 0
    barOffsetPct: float = 0.0
    barWidthPct: float = 0.0
    provisional: bool = False
    preferRatio: bool = False


class RatioGateIn(BaseModel):
    id: Optional[str] = None
    name: str
    numerator: str
    denominator: str
    min: float
    max: float
    rationale: str = ""
    enabled: bool = True


class CandidateComponentIn(BaseModel):
    id: Optional[str] = None
    name: str
    partNumber: Optional[str] = "—"
    category: Optional[str] = ""
    nominalAlloy: Optional[str] = ""
    confidence: Optional[float] = 0
    notes: Optional[str] = ""


class MaterialFamilyIn(BaseModel):
    code: str
    name: str
    gradeHint: str = ""
    status: str = "FIRM"
    description: str = ""
    totalSpectra: int = 0
    elementBands: List[ElementBandIn] = []
    ratioGates: List[RatioGateIn] = []
    candidateComponents: List[CandidateComponentIn] = []


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> Dict[str, Any]:
    kb = kb_service.load_frontend_families()
    return {
        "status": "ok",
        "engine": "rule_engine.scoring (Rule-Based Engine only, no ML)",
        "knowledgeBaseVersion": kb["version"],
        "familyCount": len(kb["families"]),
    }


# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------

@app.get("/api/knowledge-base")
def get_knowledge_base_view() -> Dict[str, Any]:
    try:
        return kb_service.list_families()
    except kb_service.KBNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/knowledge-base/validate")
def validate_family(payload: MaterialFamilyIn) -> Dict[str, Any]:
    return kb_service.validate_payload(payload.model_dump(), family_id=payload.code or "DRAFT")


@app.post("/api/knowledge-base/families")
def create_family(payload: MaterialFamilyIn) -> Dict[str, Any]:
    family_id = payload.code.strip()
    if not family_id:
        raise HTTPException(status_code=400, detail="Family code is required")
    try:
        result = kb_service.create_family(family_id, payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except kb_service.KBValidationError as e:
        raise HTTPException(status_code=422, detail={"issues": e.issues, "warnings": e.warnings})
    audit.log_event(
        action=f"Added material family {family_id} ({payload.name})",
        action_type="Knowledge Base Update",
        family_code=family_id,
        change_from="-",
        change_to=f"{len(payload.elementBands)} element bands, {len(payload.candidateComponents)} components",
        impact_text="New family added to the Rule-Based Engine's Knowledge Base",
        impact_type="positive",
    )
    return result


@app.put("/api/knowledge-base/families/{family_id}")
def update_family(family_id: str, payload: MaterialFamilyIn) -> Dict[str, Any]:
    try:
        result = kb_service.update_family(family_id, payload.model_dump())
    except kb_service.KBNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except kb_service.KBValidationError as e:
        raise HTTPException(status_code=422, detail={"issues": e.issues, "warnings": e.warnings})
    audit.log_event(
        action=f"Updated material family {family_id} ({payload.name})",
        action_type="Knowledge Base Update",
        family_code=family_id,
        change_from="previous elemental ranges / rules",
        change_to=f"{len(payload.elementBands)} element bands, {len(payload.ratioGates)} ratio gates",
        impact_text="Element ranges/rules re-saved to the Knowledge Base and reloaded by the Rule Engine",
        impact_type="positive",
    )
    return result


@app.delete("/api/knowledge-base/families/{family_id}")
def delete_family(family_id: str) -> Dict[str, Any]:
    try:
        result = kb_service.delete_family(family_id)
    except kb_service.KBNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    audit.log_event(
        action=f"Deleted material family {family_id}",
        action_type="Knowledge Base Update",
        family_code=family_id,
        change_from="entry present",
        change_to="entry removed",
        impact_text="Family removed from the Rule-Based Engine's Knowledge Base",
        impact_type="warning",
    )
    return result


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

@app.post("/api/analyze/manual")
def analyze_manual_endpoint(payload: ManualAnalyzeRequest) -> Dict[str, Any]:
    if not payload.elements:
        raise HTTPException(status_code=400, detail="At least one element value is required")
    result = analyze_manual(payload.elements, payload.analysedElements)
    audit.log_event(
        action="Ran manual EDS composition analysis",
        action_type="Calibration",
        family_code=(result.get("matchedFamilies") or [{}])[0].get("familyId", "-"),
        change_from="-",
        change_to=result.get("materialFamily") or "No match",
        impact_text=result.get("reason", ""),
        impact_type="positive" if result.get("decision") == "identified" else "neutral",
    )
    return result


@app.post("/api/analyze/file")
async def analyze_file_endpoint(file: UploadFile = File(...)) -> Dict[str, Any]:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Upload a .pdf, .docx or .doc EDS report.",
        )

    dest = UPLOADS_DIR / f"{uuid.uuid4().hex}{suffix}"
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    try:
        result = analyze_pdf(dest)
    except Exception as e:  # noqa: BLE001 - surfaced to the UI as a clear error
        raise HTTPException(status_code=422, detail=f"Extraction/prediction failed: {e}")

    result["fileName"] = file.filename
    headline = result.get("headline")
    audit.log_event(
        action=f"Analyzed uploaded report: {file.filename}",
        action_type="Calibration",
        family_code=(headline or {}).get("materialFamily") or "-",
        change_from="-",
        change_to=(headline or {}).get("materialFamily") or "No match",
        impact_text=(headline or {}).get("reason", "") if headline else "No EDS table found in report",
        impact_type="positive" if headline and headline.get("decision") == "identified" else "neutral",
    )
    return result


@app.get("/api/samples")
def list_samples() -> Dict[str, Any]:
    if not SAMPLES_DIR.exists():
        return {"samples": []}
    return {"samples": sorted(p.name for p in SAMPLES_DIR.glob("*.pdf"))}


@app.post("/api/samples/{sample_name}/analyze")
def analyze_sample_endpoint(sample_name: str) -> Dict[str, Any]:
    path = SAMPLES_DIR / sample_name
    if not path.exists() or path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="Sample not found")
    try:
        result = analyze_pdf(path)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Extraction/prediction failed: {e}")
    result["fileName"] = sample_name
    headline = result.get("headline")
    audit.log_event(
        action=f"Analyzed sample report: {sample_name}",
        action_type="Calibration",
        family_code=(headline or {}).get("materialFamily") or "-",
        change_from="-",
        change_to=(headline or {}).get("materialFamily") or "No match",
        impact_text=(headline or {}).get("reason", "") if headline else "No EDS table found in report",
        impact_type="positive" if headline and headline.get("decision") == "identified" else "neutral",
    )
    return result


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

@app.get("/api/audit-log")
def get_audit_log() -> Dict[str, Any]:
    return {"entries": audit.list_events()}


# ---------------------------------------------------------------------------
# Static frontend (built Spectral-Lab UI), served at the site root.
# Registered last so /api/* routes above always take precedence.
# ---------------------------------------------------------------------------

if FRONTEND_DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST_DIR), html=True), name="frontend")
