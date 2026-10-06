"""End-to-end Pipeline for Phases 1-7: Ingestion, Aggregation, Reference Library, Secondary Verification, Data Reconciliation Report, Trusted Store Build, and Grouped Report-Level CV."""
from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import hashlib
import json
import pandas as pd

from isp.aggregation import SiteAggregate, aggregate_site_spectra
from isp.decode import DecodedSpectrum, decode_row
from isp.engine import UnifiedISPEngine
from isp.registry import (
    COMPONENT_BY_ID,
    INTERNAL_COMPONENTS,
    MATERIAL_FAMILIES,
    map_chemistry_to_family,
    map_location_zone,
    normalize_coating,
    parse_candidate_list,
)
from isp.verification import (
    ComponentReferenceFingerprint,
    SECONDARY_NAME_TO_CANONICAL,
    SpectrumVerificationResult,
    build_reference_fingerprints,
    verify_secondary_spectrum,
)


PRIMARY_PATH = Path("data/primary/EDS_Internal_Report_Particle_Dataset.xlsx")
SECONDARY_PATH = Path("data/primary/EDS_Consolidation_SECONDARY.xlsx")
OUT_DIR = Path("data_prep/out")
STORE_PATH = Path("rule_engine/knowledge/trusted_isp_store.json")


def load_primary_dataset(path: Path = PRIMARY_PATH) -> Tuple[List[SiteAggregate], Dict[str, Dict[str, object]], Dict[str, List[str]], pd.DataFrame]:
    """Load and decode the primary validated dataset at site level."""
    sheets = pd.read_excel(path, sheet_name=None, dtype=str)
    R = sheets["Report_Particle_Dataset"].copy()
    R["_dup_idx"] = R.groupby(["source_file", "site_index"]).cumcount()
    R["site_uid"] = (
        R.source_file.str.replace(r"\W+", "_", regex=True).str[-60:]
        + "__"
        + R.site_index.astype(str)
        + "__"
        + R["_dup_idx"].astype(str)
    )
    rep_map = {f: f"R{i:04d}" for i, f in enumerate(sorted(R.source_file.unique()), 1)}
    R["report_id"] = R.source_file.map(rep_map)

    els = [c.replace("Spectrum_1_", "") for c in R.columns if c.startswith("Spectrum_1_") and "complaint" not in c]

    sites: List[SiteAggregate] = []
    site_meta: Dict[str, Dict[str, object]] = {}
    site_candidates: Dict[str, List[str]] = {}

    for _, row in R.iterrows():
        suid = str(row["site_uid"])
        rep_id = str(row["report_id"])
        internal_ids, tok_records, scope = parse_candidate_list(row.get("Probable_Internal_Source"))
        c_state, c_type, c_basis = normalize_coating(row.get("surface_coating"))
        loc_raw = row.get("location") if pd.notna(row.get("location")) else None
        loc_zone, loc_leak = map_location_zone(loc_raw, internal_ids)
        fam_id = map_chemistry_to_family(row.get("chemistry"))

        # Extract 0..5 spectra for this site
        decs: List[DecodedSpectrum] = []
        for k in range(1, 6):
            cells: Dict[str, float] = {}
            for el in els:
                v = row.get(f"Spectrum_{k}_{el}")
                if pd.notna(v) and str(v).strip() != "":
                    try:
                        cells[el] = float(v)
                    except ValueError:
                        pass
            if cells:
                decs.append(decode_row(cells, els))

        agg = aggregate_site_spectra(site_uid=suid, report_id=rep_id, spectra=decs)
        sites.append(agg)

        fold = int(hashlib.sha256(rep_id.encode()).hexdigest(), 16) % 5
        site_meta[suid] = {
            "site_uid": suid,
            "report_id": rep_id,
            "source_file": str(row["source_file"]),
            "site_index": str(row["site_index"]),
            "report_date": str(row["report_date"]) if pd.notna(row.get("report_date")) else None,
            "chemistry_raw": str(row["chemistry"]) if pd.notna(row.get("chemistry")) else None,
            "family_id": fam_id,
            "coating_raw": str(row["surface_coating"]) if pd.notna(row.get("surface_coating")) else None,
            "coating_state": c_state,
            "coating_type": c_type,
            "coating_basis": c_basis,
            "location_raw": loc_raw,
            "location_zone": loc_zone,
            "location_leak": loc_leak,
            "scope": scope,
            "fold": fold,
            "n_candidates": len(internal_ids),
            "n_valid_spectra": agg.n_valid_spectra,
            "quality_score": agg.quality_score,
        }
        if internal_ids:
            site_candidates[suid] = internal_ids

    return sites, site_meta, site_candidates, R


def run_secondary_verification_and_reconciliation(
    primary_sites: List[SiteAggregate],
    site_meta: Dict[str, Dict[str, object]],
    site_candidates: Dict[str, List[str]],
    level1_fps: Dict[str, ComponentReferenceFingerprint],
    secondary_path: Path = SECONDARY_PATH,
) -> Tuple[List[SpectrumVerificationResult], List[SiteAggregate], Dict[str, List[str]], pd.DataFrame]:
    """Run secondary spectrum similarity validation and build the Data Reconciliation Report."""
    C = pd.read_excel(secondary_path, dtype=str)
    C = C.loc[:, [c for c in C.columns if not str(c).startswith("Unnamed")]]
    el_cols = [c for c in C.columns if c not in ("Sr No.", "ComponentName", "Material Body")]

    ver_results: List[SpectrumVerificationResult] = []
    accepted_sites: List[SiteAggregate] = []
    accepted_cands: Dict[str, List[str]] = {}
    conflict_rows: List[Dict[str, object]] = []

    for idx, row in C.iterrows():
        sec_id = f"SEC_{int(row.get('Sr No.', idx + 1)):03d}"
        comp_raw = str(row.get("ComponentName", "")).strip()
        raw_els: Dict[str, float] = {}
        for el in el_cols:
            v = row.get(el)
            if pd.notna(v) and str(v).strip() not in ("", "."):
                try:
                    raw_els[el] = float(v)
                except ValueError:
                    pass

        res = verify_secondary_spectrum(sec_id, comp_raw, raw_els, level1_fps)
        ver_results.append(res)

        if res.decision == "ACCEPT" and res.mapped_component_id:
            dec = decode_row(raw_els)
            # Native labels in consolidation file
            dec.elements = {k: v for k, v in raw_els.items() if v is not None}
            dec.status = "NATIVE_LABELS"
            agg = aggregate_site_spectra(site_uid=sec_id, report_id=f"SEC_REP_{comp_raw}", spectra=[dec])
            accepted_sites.append(agg)
            accepted_cands[sec_id] = [res.mapped_component_id]
        else:
            conflict_rows.append({
                "secondary_id": res.secondary_id,
                "secondary_component": res.secondary_component_raw,
                "mapped_primary_component": res.reference_component_name or "NONE",
                "spectrum_similarity": res.spectrum_similarity,
                "supporting_elements": "; ".join(res.supporting_elements),
                "contradicting_elements": "; ".join(res.contradicting_elements),
                "element_differences": json.dumps(res.element_differences),
                "conflict_reason": res.conflict_reason,
                "final_decision": res.decision,
                "decision_source": "SPECTRUM_SIMILARITY_ENGINE",
            })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([asdict(r) for r in ver_results]).to_csv(OUT_DIR / "secondary_verification_log.csv", index=False)
    pd.DataFrame(conflict_rows).to_csv(OUT_DIR / "conflict_log.csv", index=False)

    # Build per-component Data Reconciliation Table
    rec_rows: List[Dict[str, object]] = []
    # 1. All 35 canonical internal components
    for spec in INTERNAL_COMPONENTS:
        cid = spec.component_id
        fp = level1_fps[cid]
        p_sites_all = [suid for suid, cands in site_candidates.items() if cid in cands]
        p_spec_sites = [s for s in primary_sites if s.site_uid in p_sites_all and s.n_valid_spectra > 0]
        p_spec_cnt = sum(s.n_valid_spectra for s in p_spec_sites)

        sec_matches = [r for r in ver_results if r.mapped_component_id == cid]
        sec_cnt = len(sec_matches)
        acc_cnt = sum(1 for r in sec_matches if r.decision == "ACCEPT")
        rev_cnt = sum(1 for r in sec_matches if r.decision == "REVIEW")
        rej_cnt = sum(1 for r in sec_matches if r.decision == "REJECT")
        mean_sim = round(sum(r.spectrum_similarity for r in sec_matches) / sec_cnt, 4) if sec_cnt else None
        sup_els = sorted({el for r in sec_matches for el in r.supporting_elements})
        con_els = sorted({el for r in sec_matches for el in r.contradicting_elements})
        reasons = sorted({r.conflict_reason.split(":")[0] for r in sec_matches})

        rec_rows.append({
            "Component": spec.canonical_name,
            "Component_ID": cid,
            "Primary_Sample_Count": len(p_sites_all),
            "Primary_Reports": fp.n_reports,
            "Validated_Spectrum_Count": p_spec_cnt,
            "Secondary_Sample_Count": sec_cnt,
            "Spectrum_Similarity": mean_sim if mean_sim is not None else "N/A",
            "Chemistry_Agreement": (
                "COMPATIBLE" if acc_cnt > 0 or (rev_cnt > 0 and mean_sim and mean_sim >= 0.70)
                else ("CONFLICT_SITE_OR_GRADE" if rej_cnt > 0 else ("NO_PRIMARY_SPECTRA" if sec_cnt > 0 and p_spec_cnt == 0 else "N/A"))
            ),
            "Element_Agreement": ", ".join(sup_els) if sup_els else "None",
            "Conflicting_Spectra": rej_cnt,
            "Accepted_Secondary_Records": acc_cnt,
            "Review_Secondary_Records": rev_cnt,
            "Rejected_Secondary_Records": rej_cnt,
            "Reason_For_Decision": "; ".join(reasons) if reasons else "No secondary records",
        })

    # 2. Secondary-only components excluded from internal targets
    unmapped_names = sorted({r.secondary_component_raw for r in ver_results if r.mapped_component_id is None})
    for uname in unmapped_names:
        sec_m = [r for r in ver_results if r.secondary_component_raw == uname]
        rec_rows.append({
            "Component": f"{uname} [Secondary-Only]",
            "Component_ID": "EXCLUDED_SECONDARY_ONLY",
            "Primary_Sample_Count": 0,
            "Primary_Reports": 0,
            "Validated_Spectrum_Count": 0,
            "Secondary_Sample_Count": len(sec_m),
            "Spectrum_Similarity": 0.0,
            "Chemistry_Agreement": "NO_PRIMARY_COUNTERPART",
            "Element_Agreement": "None",
            "Conflicting_Spectra": 0,
            "Accepted_Secondary_Records": 0,
            "Review_Secondary_Records": 0,
            "Rejected_Secondary_Records": len(sec_m),
            "Reason_For_Decision": "NO_PRIMARY_COUNTERPART: Excluded from internal targets",
        })

    rec_df = pd.DataFrame(rec_rows)
    rec_df.to_csv(OUT_DIR / "data_reconciliation_report.csv", index=False)
    return ver_results, accepted_sites, accepted_cands, rec_df


def run_grouped_validation(
    sites: List[SiteAggregate],
    site_meta: Dict[str, Dict[str, object]],
    site_candidates: Dict[str, List[str]],
) -> Dict[str, object]:
    """Run 5-fold Report-Grouped Cross-Validation and Leakage Checks (Phase 7)."""
    site_by_uid = {s.site_uid: s for s in sites}
    internal_uids = [u for u in site_candidates if site_candidates[u]]
    external_uids = [u for u, m in site_meta.items() if m["scope"] == "EXTERNAL_ONLY"]

    # Leakage verification 1: Ensure every report_id maps to exactly 1 fold
    rep_folds: Dict[str, Set[int]] = {}
    for u, m in site_meta.items():
        rep_folds.setdefault(str(m["report_id"]), set()).add(int(m["fold"]))  # type: ignore[arg-type]
    leaked_reports = [r for r, fset in rep_folds.items() if len(fset) > 1]
    assert len(leaked_reports) == 0, f"Report-level split leakage detected: {leaked_reports}"

    set_hits = 0
    top1_hits = 0
    high_conf_total = 0
    high_conf_correct = 0
    ambiguous_total = 0
    ambiguous_set_hits = 0
    spec_total = 0
    spec_set_hits = 0
    spec_top1_hits = 0
    loc_only_hits = 0

    for test_fold in range(5):
        train_sites = [s for s in sites if site_meta[s.site_uid]["fold"] != test_fold and s.site_uid in site_candidates]
        train_cands = {s.site_uid: site_candidates[s.site_uid] for s in train_sites}
        train_fps = build_reference_fingerprints(train_sites, train_cands, trust_level=1)
        engine = UnifiedISPEngine.fit_from_trusted_sites(
            sites=train_sites,
            site_meta=site_meta,
            site_candidates=train_cands,
            fingerprints=train_fps,
            data_release=f"cv_fold_{test_fold}",
        )

        # Location-only baseline from training fold
        zone_top: Dict[str, str] = {}
        for z, cdict in engine.zone_comp_counts.items():
            if cdict:
                zone_top[z] = max(cdict, key=cdict.get)

        test_uids = [u for u in internal_uids if site_meta[u]["fold"] == test_fold]
        for u in test_uids:
            s = site_by_uid[u]
            m = site_meta[u]
            truth = set(site_candidates[u])
            raw_specs = [sp.raw_cells for sp in s.spectra]
            pred = engine.predict(
                spectra_inputs=raw_specs,
                chemistry_raw=m["chemistry_raw"],  # type: ignore[arg-type]
                surface_coating_raw=m["coating_raw"],  # type: ignore[arg-type]
                location_raw=m["location_raw"],  # type: ignore[arg-type]
                site_uid=u,
                report_id=str(m["report_id"]),
            )
            pred_ids = [c.component_id for c in pred.candidates]
            hit_any = bool(set(pred_ids) & truth)
            hit_top1 = bool(pred_ids and pred_ids[0] in truth)

            if hit_any:
                set_hits += 1
            if hit_top1:
                top1_hits += 1

            if pred.prediction_status == "HIGH_CONFIDENCE":
                high_conf_total += 1
                if pred.predicted_component_id in truth:
                    high_conf_correct += 1
            elif pred.prediction_status == "AMBIGUOUS":
                ambiguous_total += 1
                if hit_any:
                    ambiguous_set_hits += 1

            if s.n_valid_spectra > 0:
                spec_total += 1
                if hit_any:
                    spec_set_hits += 1
                if hit_top1:
                    spec_top1_hits += 1

            z_guess = zone_top.get(str(m["location_zone"]), "IC_STUD")
            if z_guess in truth:
                loc_only_hits += 1

    # Evaluate external contaminant rejection rate
    full_fps = build_reference_fingerprints(sites, site_candidates, trust_level=1)
    full_engine = UnifiedISPEngine.fit_from_trusted_sites(sites, site_meta, site_candidates, full_fps)
    ext_abstained = 0
    ext_total = 0
    for u in external_uids:
        s = site_by_uid[u]
        m = site_meta[u]
        pred = full_engine.predict(
            spectra_inputs=[sp.raw_cells for sp in s.spectra],
            chemistry_raw=m["chemistry_raw"],  # type: ignore[arg-type]
            surface_coating_raw=m["coating_raw"],  # type: ignore[arg-type]
            location_raw=m["location_raw"],  # type: ignore[arg-type]
            site_uid=u,
            report_id=str(m["report_id"]),
        )
        ext_total += 1
        if pred.prediction_status in ("UNKNOWN", "AMBIGUOUS"):
            ext_abstained += 1

    n_int = len(internal_uids)
    metrics = {
        "n_internal_sites": n_int,
        "n_internal_reports": len({site_meta[u]["report_id"] for u in internal_uids}),
        "n_spectrum_internal_sites": spec_total,
        "report_level_split_leakage": 0,
        "candidate_set_coverage": round(set_hits / max(1, n_int), 4),
        "top1_candidate_compatibility_rate": round(top1_hits / max(1, n_int), 4),
        "high_confidence_count": high_conf_total,
        "high_confidence_selective_precision": round(high_conf_correct / max(1, high_conf_total), 4),
        "ambiguous_count": ambiguous_total,
        "ambiguous_set_coverage": round(ambiguous_set_hits / max(1, ambiguous_total), 4),
        "spectrum_bearing_set_coverage": round(spec_set_hits / max(1, spec_total), 4),
        "spectrum_bearing_top1_rate": round(spec_top1_hits / max(1, spec_total), 4),
        "location_only_baseline_top1": round(loc_only_hits / max(1, n_int), 4),
        "external_contaminant_non_single_rate": round(ext_abstained / max(1, ext_total), 4),
    }
    (OUT_DIR / "validation_report.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def serialize_trusted_store(
    engine: UnifiedISPEngine,
    ver_results: List[SpectrumVerificationResult],
    metrics: Dict[str, object],
    path: Path = STORE_PATH,
) -> None:
    """Serialize the trusted reference store (Level 1 + Verified Level 2) to JSON for zero-dependency runtime."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fp_dict = {cid: asdict(fp) for cid, fp in engine.fingerprints.items()}
    payload = {
        "version": "2.0.0",
        "data_release": engine.data_release,
        "calibrated_reports": engine.calibrated_reports,
        "fingerprints": fp_dict,
        "family_comp_counts": engine.family_comp_counts,
        "coating_comp_counts": engine.coating_comp_counts,
        "zone_comp_counts": engine.zone_comp_counts,
        "comp_report_counts": engine.comp_report_counts,
        "comp_site_counts": engine.comp_site_counts,
        "cooccurrence_sets": {k: sorted(v) for k, v in engine.cooccurrence_sets.items()},
        "secondary_verification_summary": {
            "total_secondary_spectra": len(ver_results),
            "accepted_level2": sum(1 for r in ver_results if r.decision == "ACCEPT"),
            "review_pending": sum(1 for r in ver_results if r.decision == "REVIEW"),
            "rejected_conflicting": sum(1 for r in ver_results if r.decision == "REJECT"),
            "excluded_no_counterpart": sum(1 for r in ver_results if r.decision == "EXCLUDED"),
        },
        "validation_metrics": metrics,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    print("1. Loading and decoding Primary Validated Dataset (Level 1)...")
    sites, site_meta, site_candidates, _ = load_primary_dataset()
    level1_fps = build_reference_fingerprints(sites, site_candidates, trust_level=1)

    print("2. Running Secondary Spectrum Similarity Verification & Data Reconciliation...")
    ver_results, acc_sites, acc_cands, rec_df = run_secondary_verification_and_reconciliation(
        sites, site_meta, site_candidates, level1_fps
    )
    acc_n = sum(1 for r in ver_results if r.decision == "ACCEPT")
    rev_n = sum(1 for r in ver_results if r.decision == "REVIEW")
    rej_n = sum(1 for r in ver_results if r.decision == "REJECT")
    exc_n = sum(1 for r in ver_results if r.decision == "EXCLUDED")
    print(f"   Secondary Verification (176 spectra): ACCEPT={acc_n}, REVIEW={rev_n}, REJECT={rej_n}, EXCLUDED={exc_n}")

    print("3. Building Trusted Data Store (Level 1 Validated + Level 2 Verified Supplementary)...")
    trusted_sites = list(sites) + acc_sites
    trusted_cands = dict(site_candidates)
    trusted_cands.update(acc_cands)
    trusted_fps = build_reference_fingerprints(trusted_sites, trusted_cands, trust_level=1)
    for r in ver_results:
        if r.decision == "ACCEPT" and r.mapped_component_id and r.mapped_component_id in trusted_fps:
            trusted_fps[r.mapped_component_id].trust_level = 2

    engine = UnifiedISPEngine.fit_from_trusted_sites(
        sites=sites,
        site_meta=site_meta,
        site_candidates=site_candidates,
        fingerprints=trusted_fps,
        data_release="r2.0-validated",
    )

    print("4. Running Phase 7 Grouped Report-Level Cross-Validation & Leakage Suite...")
    metrics = run_grouped_validation(sites, site_meta, site_candidates)
    for k, v in metrics.items():
        print(f"   {k}: {v}")

    print("5. Serializing Trusted Store to", STORE_PATH)
    serialize_trusted_store(engine, ver_results, metrics)


if __name__ == "__main__":
    main()
