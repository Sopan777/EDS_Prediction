"""
backend/analyze_service.py
===========================
The PDF -> EDS Extraction -> Data Cleaning/Normalization -> Rule-Based Engine
-> Component Prediction pipeline (requirement 2), wrapped for the web API.

This is a thin adapter: all real work is done by the existing, unmodified
eds_core pipeline -
    eds_core/eds_pipeline.py        (PDF ingest -> table extraction)
    eds_core/rule_engine/normalize.py   (cleaning / normalization)
    eds_core/rule_engine/scoring.py     (the Rule-Based Engine + Knowledge Base)

No ML model (CatBoost/RandomForest/XGBoost/ExtraTrees) is imported or called
anywhere in this module or anything it calls - see eds_core/eds_pipeline.py's
own docstring, which documents that the ML path (predictor.py) was already
removed from this exact flow because no trained model artifacts exist.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import backend.paths  # noqa: F401  (wires eds_core onto sys.path)

from eds_pipeline import run_pipeline
from rule_engine.normalize import normalize_spectrum
from rule_engine.scoring import (
    Decision,
    Prediction,
    get_knowledge_base,
    predict_spectrum,
)


def _rule_based_result(prediction: Dict[str, Any]) -> Dict[str, Any]:
    """Reshape a Prediction.to_dict() into the Analyzer's result contract.

    Requirement 7 fields:
      - validation status         -> `status`
      - matched rules              -> `matchedFamilies` (every family considered,
                                       each with its individual checks)
      - predicted component        -> `predictedComponent` / `candidateComponents`
      - Rule-Based Score, labelled -> `ruleBasedScore` (0-100, clearly not an ML
                                       probability - see `scoreLabel`)
      - reason/explanation         -> `reason`
      - Unknown / No Match         -> `decision === "unknown"`
    """
    decision = prediction.get("decision", "unknown")
    compatibility = prediction.get("compatibility", 0.0)
    families = prediction.get("families", [])

    status = {
        "identified": "matched",
        "ambiguous": "ambiguous",
        "unknown": "no_match",
    }.get(decision, "no_match")

    return {
        "decision": decision,
        "status": status,
        "materialFamily": prediction.get("material_family"),
        "gradeHint": prediction.get("grade_hint"),
        "ruleBasedScore": round(compatibility * 100, 1),
        "scoreLabel": "Rule-Based Score",
        "margin": prediction.get("margin", 0.0),
        "reason": prediction.get("reason", ""),
        "predictedComponent": (prediction.get("candidate_components") or [None])[0],
        "candidateComponents": prediction.get("candidate_components", []),
        "caveats": prediction.get("caveats", []),
        "quality": prediction.get("quality", {}),
        "matchedFamilies": [
            {
                "familyId": f.get("family_id"),
                "label": f.get("label"),
                "verdict": f.get("verdict"),
                "compatibility": round(f.get("compatibility", 0.0) * 100, 1),
                "candidateComponents": f.get("candidate_components", []),
                "blocking": f.get("blocking", []),
                "unevaluableElements": f.get("unevaluable_elements", []),
                "unexplainedElements": f.get("unexplained_elements", []),
                "checks": f.get("checks", []),
            }
            for f in families
        ],
        "engine": "rule_engine.scoring (deterministic Rule-Based Engine, no ML)",
        "knowledgeBaseVersion": get_knowledge_base().version,
    }


def _extracted_elements(values: Dict[str, Any], analysed_elements: List[str]) -> List[Dict[str, Any]]:
    """Cleaned / normalised elements for display, independent of any one family."""
    ns = normalize_spectrum(values, analysed_elements=analysed_elements)
    out = []
    for element, reading in sorted(ns.readings.items()):
        out.append({
            "element": element,
            "state": reading.state.value,
            "rawWt": reading.raw_wt,
            "metalWt": None if reading.metal_wt is None else round(reading.metal_wt, 3),
            "sigma": None if reading.sigma is None else round(reading.sigma, 4),
            "inAlloyBasis": reading.in_alloy_basis,
        })
    return out, ns


def analyze_manual(values: Dict[str, Any], analysed_elements: Optional[List[str]] = None) -> Dict[str, Any]:
    """Manual EDS entry (wt%) -> cleaned elements + Rule-Based Engine result."""
    analysed = analysed_elements if analysed_elements else list(values.keys())
    elements, ns = _extracted_elements(values, analysed)
    prediction = predict_spectrum(values, analysed_elements=analysed)
    result = _rule_based_result(prediction.to_dict())
    result["source"] = {"type": "manual", "label": "Manual EDS entry"}
    result["extractedElements"] = elements
    result["validation"] = {
        "warnings": list(ns.warnings),
        "dataQualityErrors": list(ns.data_quality_errors),
        "unresolvedKeys": list(ns.unresolved_keys),
        "isValid": not ns.data_quality_errors,
    }
    return result


def analyze_pdf(pdf_path: Path) -> Dict[str, Any]:
    """Full pipeline: PDF -> extraction -> normalization -> Rule-Based Engine.

    Mirrors eds_pipeline.run_pipeline (per-table pooled prediction + a
    per-spectrum prediction for every row), reshaped into the Analyzer
    contract and flattened into one primary "headline" result (the
    highest-compatibility table/spectrum) plus every table for full detail.
    """
    raw = run_pipeline(str(pdf_path), per_spectrum=True)

    tables_out: List[Dict[str, Any]] = []
    best: Optional[Dict[str, Any]] = None

    for t_idx, table in enumerate(raw.get("eds_tables", []), start=1):
        columns = [e for e in table.get("elements", []) if e != "Total"]
        pooled_pred = table.get("pooled_prediction", {})
        pooled_result = _rule_based_result(pooled_pred)
        pooled_result["source"] = {
            "type": "pdf_table",
            "label": f"{table.get('table_name', 'EDS Table')} (page {table.get('page')})",
        }

        spectra_out = []
        for spectrum in table.get("spectra", []):
            values = {k: v for k, v in spectrum.get("values", {}).items() if k != "Total" and v is not None}
            elements, ns = _extracted_elements(values, columns) if values else ([], None)
            pred = spectrum.get("prediction") or {}
            spec_result = _rule_based_result(pred) if pred else None
            spectra_out.append({
                "spectrum": spectrum.get("spectrum"),
                "rawValues": spectrum.get("values", {}),
                "extractedElements": elements,
                "validation": {
                    "warnings": list(ns.warnings) if ns else [],
                    "dataQualityErrors": list(ns.data_quality_errors) if ns else [],
                    "isValid": (not ns.data_quality_errors) if ns else False,
                },
                "result": spec_result,
            })

        table_entry = {
            "tableName": table.get("table_name"),
            "page": table.get("page"),
            "columns": columns,
            "pooledResult": pooled_result,
            "spectra": spectra_out,
        }
        tables_out.append(table_entry)

        score = pooled_result.get("ruleBasedScore", 0.0)
        if best is None or score > best["pooledResult"]["ruleBasedScore"]:
            best = table_entry

    settings = raw.get("prediction_settings", {})
    return {
        "fileName": pdf_path.name,
        "engine": settings.get("engine", "rule_engine.scoring"),
        "knowledgeBaseVersion": settings.get("knowledge_base_version") or get_knowledge_base().version,
        "tables": tables_out,
        "headline": best["pooledResult"] if best else None,
        "headlineTable": best["tableName"] if best else None,
        "message": raw.get("message"),
    }
