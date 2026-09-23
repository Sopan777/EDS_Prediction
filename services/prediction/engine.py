"""
services/prediction/engine.py
=============================
Wraps rule_engine.scoring for single and multi-spectrum particle prediction,
component-level ranking from statistical fingerprints, conflict detection,
and analysis history persistence.
"""

import json
import math
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from apps.history.models import AnalysisHistory
from rule_engine.normalize import normalize_spectrum
from rule_engine.scoring import (
    Decision,
    Prediction,
    predict_particle,
    predict_spectrum,
)
from rule_engine.component_scoring import (
    ComponentScore,
    decide_component,
    rank_components,
)
from rule_engine.conflict_detector import detect_conflict, ConflictResult
from services.audit.logger import log_event
from services.knowledge.kb import format_material_family, get_all_families_mapped, get_kb


def format_candidate_component(
    cand: ComponentScore,
    family_id: str,
    grade_hint: str = "",
    is_top: bool = False,
) -> Dict[str, Any]:
    """Format a ComponentScore into a clean, honest candidate record."""
    compat_pct = round(cand.compatibility * 100)
    
    notes = (
        f"Statistical match to {cand.display_name} reference fingerprint ({cand.fingerprint_quality} confidence, "
        f"{cand.sample_count} spectra). Evidence sufficiency: {cand.evidence_sufficiency * 100:.0f}%."
    )

    return {
        "id": f"cand-{cand.component_id.lower().replace('_', '-')}",
        "name": cand.display_name,
        "component_id": cand.component_id,
        "partNumber": cand.component_id,
        "category": f"{cand.fingerprint_quality} Quality Reference ({cand.sample_count} spectra)",
        "nominalAlloy": grade_hint or "Empirical Reference",
        "confidence": compat_pct,
        "compatibility": round(cand.compatibility, 4),
        "sampleCount": cand.sample_count,
        "fingerprintQuality": cand.fingerprint_quality,
        "decision": cand.decision,
        "matchedElements": cand.matched_elements,
        "missingElements": cand.missing_elements,
        "evidenceSufficiency": round(cand.evidence_sufficiency, 3),
        "elementDistances": {k: round(v, 2) for k, v in cand.element_distances.items()},
        "notes": notes,
        "isTopMatch": is_top,
    }


def run_prediction(
    spectra: Optional[List[Dict[str, float]]] = None,
    composition: Optional[Dict[str, float]] = None,
    analysed_elements: Optional[List[str]] = None,
    source_type: str = "manual",
    source_filename: Optional[str] = None,
    declared_material: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute prediction for single spectrum or multiple spectra (pooled particle).
    Calculates pooled average, predicts material family, checks declared material conflict,
    and statistically matches and ranks candidate components.
    """
    start_time = time.perf_counter()
    kb = get_kb()
    if not kb:
        raise RuntimeError("Knowledge base is not loaded.")

    # Normalize input spectra list
    spectra_list: List[Dict[str, float]] = []
    if spectra and len(spectra) > 0:
        spectra_list = [s for s in spectra if s]
    elif composition:
        spectra_list = [composition]

    if not spectra_list:
        raise ValueError("No spectral composition supplied for prediction.")

    # Derive combined elements if not provided
    if not analysed_elements:
        all_elem = set()
        for s in spectra_list:
            all_elem.update(s.keys())
        analysed_elements = sorted(list(all_elem))

    is_pooled = len(spectra_list) > 1

    # Execute deterministic rule engine for family
    if is_pooled:
        prediction: Prediction = predict_particle(
            spectra_list,
            analysed_elements=analysed_elements,
            knowledge=kb,
        )
        # Compute individual predictions for inspection
        per_spectrum_results = []
        for idx, spec in enumerate(spectra_list):
            try:
                single_pred = predict_spectrum(
                    spec,
                    analysed_elements=analysed_elements,
                    knowledge=kb,
                )
                per_spectrum_results.append({
                    "spectrumIndex": idx + 1,
                    "label": f"Spectrum {idx + 1}",
                    "composition": spec,
                    "decision": single_pred.decision.value,
                    "family": single_pred.top.label if single_pred.top else "Unknown",
                    "compatibilityPct": round((single_pred.top.compatibility if single_pred.top else 0.0) * 100),
                })
            except Exception:
                pass
    else:
        prediction = predict_spectrum(
            spectra_list[0],
            analysed_elements=analysed_elements,
            knowledge=kb,
        )
        per_spectrum_results = [{
            "spectrumIndex": 1,
            "label": "Spectrum 1",
            "composition": spectra_list[0],
            "decision": prediction.decision.value,
            "family": prediction.top.label if prediction.top else "Unknown",
            "compatibilityPct": round((prediction.top.compatibility if prediction.top else 0.0) * 100),
        }]

    elapsed_s = round(time.perf_counter() - start_time, 4)
    decision_val = prediction.decision.value
    top_score = prediction.top

    all_families_mapped = get_all_families_mapped()
    top_family_mapped = None
    if top_score:
        for f in all_families_mapped:
            if f["code"] == top_score.family_id:
                top_family_mapped = f
                break

    if not top_family_mapped:
        top_family_mapped = all_families_mapped[0] if all_families_mapped else None

    # Calculate pooled average composition across spectra
    pooled_average: Dict[str, float] = {}
    for elem in analysed_elements:
        vals = [s[elem] for s in spectra_list if elem in s and s[elem] is not None]
        if vals:
            pooled_average[elem] = round(sum(vals) / len(vals), 2)

    # Base compatibility percentage - HONEST, NO ARTIFICIAL INFLATION
    comp_pct = round((top_score.compatibility if top_score else 0.0) * 100)

    # Normalise pooled average spectrum for component scoring
    norm_pooled = normalize_spectrum(pooled_average, analysed_elements=analysed_elements)

    # Determine candidate family IDs to scope component matching
    candidate_family_ids: List[str] = []
    if top_score and decision_val == Decision.IDENTIFIED.value:
        candidate_family_ids = [top_score.family_id]
    elif decision_val == Decision.AMBIGUOUS.value:
        candidate_family_ids = [f.family_id for f in prediction.families]
    else:
        # Fallback or unknown: consider all families
        candidate_family_ids = list(kb.families.keys())

    # Component-level matching against statistical fingerprints
    raw_ranked_components = rank_components(
        spectrum=norm_pooled,
        candidate_family_ids=candidate_family_ids,
        top_n=10,
    )
    comp_decision_str, top_comp_score = decide_component(raw_ranked_components)

    candidates_list: List[Dict[str, Any]] = []
    for idx, cand in enumerate(raw_ranked_components):
        is_top = (idx == 0)
        formatted = format_candidate_component(
            cand=cand,
            family_id=top_score.family_id if top_score else "REF",
            grade_hint=top_score.grade_hint if top_score else "",
            is_top=is_top,
        )
        candidates_list.append(formatted)

    top_candidate = candidates_list[0] if candidates_list else None

    # Constraint checks from top family score
    checks_list = []
    if top_score:
        for chk in top_score.checks:
            checks_list.append(chk.to_dict())

    # Build caveats with multi-spectrum notes
    caveats_list = list(prediction.caveats)
    if is_pooled:
        caveats_list.insert(
            0,
            f"Multi-spectrum corroborated: {len(spectra_list)} spectra pooled across particle.",
        )

    # Conflict Detection: check declared material metadata against predicted family
    conflict_result = detect_conflict(
        declared_material=declared_material,
        prediction_family_id=top_score.family_id if top_score else None,
        prediction_family_label=top_score.label if top_score else None,
    )
    if conflict_result.has_conflict:
        caveats_list.append(f"MATERIAL CONFLICT: {conflict_result.message}")
        if conflict_result.severity == "critical" and decision_val == Decision.IDENTIFIED.value:
            # Flag decision state as conflict if declared material is strongly violated
            decision_val = Decision.CONFLICT.value

    # Warnings aggregation
    warnings_list: List[str] = []
    if decision_val == Decision.AMBIGUOUS.value:
        warnings_list.append("Ambiguous material family: separation is within measurement uncertainty.")
    elif decision_val == Decision.INSUFFICIENT_DATA.value:
        warnings_list.append("Insufficient data: too few alloy elements measured to establish identity.")
    elif decision_val == Decision.UNKNOWN.value:
        warnings_list.append("Unknown material: composition does not match any known reference family.")
    elif decision_val == Decision.CONFLICT.value:
        warnings_list.append(f"Material conflict: {conflict_result.message}")

    if top_candidate and top_candidate.get("fingerprintQuality") == "LOW":
        warnings_list.append(
            f"Component '{top_candidate['name']}' has limited reference data "
            f"({top_candidate.get('sampleCount', 0)} spectra); match should be reviewed."
        )

    # Persist to AnalysisHistory
    try:
        hist_id = f"hist-{int(time.time() * 1000)}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        AnalysisHistory.objects.create(
            id=hist_id,
            timestamp=now_str,
            source_type=f"{source_type}_pooled" if is_pooled else source_type,
            filename=source_filename or f"Manual Entry ({len(spectra_list)} spectra)",
            composition_json=json.dumps(pooled_average),
            decision=decision_val,
            material_family=top_score.label if top_score else "Unknown",
            grade_hint=top_score.grade_hint if top_score else "",
            compatibility=top_score.compatibility if top_score else 0.0,
            candidate_components_json=json.dumps([c["name"] for c in candidates_list]),
            processing_time_s=elapsed_s,
        )

        top_comp_str = f" -> Predicted Component: {top_candidate['name']}" if top_candidate else ""
        log_event(
            user_name="Lab Operator",
            user_role="Snr. Metallurgist",
            action=f"Particle Microanalysis: {decision_val.upper()} {top_score.label if top_score else 'Unknown'}{top_comp_str} ({len(spectra_list)} spectra pooled)",
            action_type="Calibration",
            entity_id=top_score.family_id if top_score else "None",
            details={
                "source": source_filename or "wt% input",
                "spectra_count": len(spectra_list),
                "is_pooled": is_pooled,
                "compatibility": f"{comp_pct}%",
                "top_candidate": top_candidate["name"] if top_candidate else None,
                "candidates_count": len(candidates_list),
                "component_decision": comp_decision_str,
                "conflict": conflict_result.has_conflict,
            },
            impact_type="positive" if decision_val == "identified" else "neutral",
        )
    except Exception as db_err:
        print(f"Warning: Failed to write analysis record to DB: {db_err}")

    # Evidence details
    evidence_data = {
        "matched_elements": [e for e in analysed_elements if pooled_average.get(e, 0) > 0],
        "analysed_elements": analysed_elements,
        "n_analysed_elements": len(analysed_elements),
        "alloy_signal_pct": norm_pooled.alloy_total,
        "contamination_fraction": norm_pooled.contamination_fraction,
        "coating_fraction": norm_pooled.coating_fraction,
    }

    return {
        # Standardized modern structure
        "status": decision_val,
        "decision": decision_val,
        "materialFamily": top_score.label if top_score else "Unclassified Material",
        "familyCode": top_score.family_id if top_score else None,
        "gradeHint": top_score.grade_hint if top_score else None,
        "compatibility": top_score.compatibility if top_score else 0.0,
        "compatibilityPct": comp_pct,
        "margin": round(prediction.margin, 3),
        "reason": prediction.reason,
        "processingTime": f"{elapsed_s:.2f}s",
        "isPooled": is_pooled,
        "spectraCount": len(spectra_list),
        "allSpectra": spectra_list,
        "perSpectrum": per_spectrum_results,
        "pooledAverage": pooled_average,
        "topCandidate": top_candidate,
        "candidateComponents": candidates_list,
        "caveats": caveats_list,
        "checks": checks_list,
        "topFamily": top_family_mapped,
        "extractedComposition": pooled_average,
        "allFamiliesScored": [f.to_dict() for f in prediction.families],
        # Component & Evidence additions
        "material_family": {
            "id": top_score.family_id if top_score else None,
            "name": top_score.label if top_score else "Unclassified Material",
            "compatibility": round(top_score.compatibility, 4) if top_score else 0.0,
            "grade_hint": top_score.grade_hint if top_score else None,
        },
        "component_prediction": {
            "component": top_candidate["name"] if top_candidate else None,
            "component_id": top_candidate.get("component_id") if top_candidate else None,
            "compatibility": top_candidate.get("compatibility", 0.0) if top_candidate else 0.0,
            "fingerprint_quality": top_candidate.get("fingerprintQuality") if top_candidate else None,
            "sample_count": top_candidate.get("sampleCount", 0) if top_candidate else 0,
            "decision": comp_decision_str,
        } if top_candidate else None,
        "candidates": candidates_list,
        "evidence": evidence_data,
        "conflict": {
            "has_conflict": conflict_result.has_conflict,
            "severity": conflict_result.severity,
            "message": conflict_result.message,
            "declared_material": conflict_result.declared_material,
            "declared_family": conflict_result.declared_family,
        },
        "warnings": warnings_list,
    }
