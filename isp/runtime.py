"""Runtime loader and API adapter for the Unified Internal-Source Prediction Engine (Phase 8).

Uses Python standard library only (no pandas/openpyxl required at inference time).
Loads `rule_engine/knowledge/trusted_isp_store.json` (Level 1 Validated + Level 2 Verified Supplementary).
"""
from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional
import json

from isp.engine import UnifiedISPEngine, UnifiedPredictionResult
from isp.verification import ComponentReferenceFingerprint, ElementFingerprintStats

STORE_FILE = Path(__file__).resolve().parent.parent / "rule_engine" / "knowledge" / "trusted_isp_store.json"
RECONCILIATION_CSV = Path(__file__).resolve().parent.parent / "data_prep" / "out" / "data_reconciliation_report.csv"

_ENGINE_CACHE: Optional[UnifiedISPEngine] = None
_RAW_STORE_CACHE: Optional[Dict[str, object]] = None


def load_trusted_store(force_reload: bool = False) -> Dict[str, object]:
    global _RAW_STORE_CACHE
    if _RAW_STORE_CACHE is not None and not force_reload:
        return _RAW_STORE_CACHE
    if not STORE_FILE.exists():
        raise FileNotFoundError(f"Trusted ISP store not found at {STORE_FILE}. Run `python -m isp.pipeline` first.")
    _RAW_STORE_CACHE = json.loads(STORE_FILE.read_text(encoding="utf-8"))
    return _RAW_STORE_CACHE


def get_isp_engine(force_reload: bool = False) -> UnifiedISPEngine:
    """Return cached singleton UnifiedISPEngine loaded from the trusted store."""
    global _ENGINE_CACHE
    if _ENGINE_CACHE is not None and not force_reload:
        return _ENGINE_CACHE

    data = load_trusted_store(force_reload=force_reload)
    raw_fps: Dict[str, Dict[str, object]] = data.get("fingerprints", {})  # type: ignore[assignment]
    fps: Dict[str, ComponentReferenceFingerprint] = {}
    for cid, fdict in raw_fps.items():
        el_map: Dict[str, ElementFingerprintStats] = {}
        for el, edict in (fdict.get("elements") or {}).items():  # type: ignore[union-attr]
            el_map[el] = ElementFingerprintStats(
                element=str(edict["element"]),
                median=float(edict["median"]),
                iqr=float(edict["iqr"]),
                mad=float(edict["mad"]),
                min_val=float(edict["min_val"]),
                max_val=float(edict["max_val"]),
                sigma_eff=float(edict["sigma_eff"]),
                frequency=float(edict["frequency"]),
                n_sites=int(edict["n_sites"]),
            )
        ratios_map = {
            rname: (float(rvals[0]), float(rvals[1]), float(rvals[2]))
            for rname, rvals in (fdict.get("ratios") or {}).items()  # type: ignore[union-attr]
        }
        fps[cid] = ComponentReferenceFingerprint(
            component_id=str(fdict["component_id"]),
            canonical_name=str(fdict["canonical_name"]),
            trust_level=int(fdict.get("trust_level", 1)),  # type: ignore[arg-type]
            n_reports=int(fdict.get("n_reports", 0)),  # type: ignore[arg-type]
            n_sites=int(fdict.get("n_sites", 0)),  # type: ignore[arg-type]
            n_single_candidate_sites=int(fdict.get("n_single_candidate_sites", 0)),  # type: ignore[arg-type]
            n_spectra=int(fdict.get("n_spectra", 0)),  # type: ignore[arg-type]
            quality=str(fdict.get("quality", "NONE")),
            elements=el_map,
            ratios=ratios_map,
        )

    cooccur = {
        k: set(v) for k, v in (data.get("cooccurrence_sets") or {}).items()  # type: ignore[union-attr]
    }
    _ENGINE_CACHE = UnifiedISPEngine(
        fingerprints=fps,
        family_comp_counts=data.get("family_comp_counts", {}),  # type: ignore[arg-type]
        coating_comp_counts=data.get("coating_comp_counts", {}),  # type: ignore[arg-type]
        zone_comp_counts=data.get("zone_comp_counts", {}),  # type: ignore[arg-type]
        comp_report_counts={k: int(v) for k, v in (data.get("comp_report_counts") or {}).items()},  # type: ignore[union-attr]
        comp_site_counts={k: int(v) for k, v in (data.get("comp_site_counts") or {}).items()},  # type: ignore[union-attr]
        cooccurrence_sets=cooccur,
        calibrated_reports=int(data.get("calibrated_reports", 150)),  # type: ignore[arg-type]
        data_release=str(data.get("data_release", "r2.0-validated")),
    )
    return _ENGINE_CACHE


def predict_internal_source_dict(
    spectra_inputs: List[Dict[str, float]],
    chemistry_raw: Optional[str] = None,
    surface_coating_raw: Optional[str] = None,
    location_raw: Optional[str] = None,
    site_uid: str = "query_site",
    report_id: str = "query_report",
) -> Dict[str, object]:
    """Run unified prediction and format as JSON-serializable dictionary (Section C & D contract)."""
    engine = get_isp_engine()
    res: UnifiedPredictionResult = engine.predict(
        spectra_inputs=spectra_inputs,
        chemistry_raw=chemistry_raw,
        surface_coating_raw=surface_coating_raw,
        location_raw=location_raw,
        site_uid=site_uid,
        report_id=report_id,
    )
    return asdict(res)
