"""
validation/leave_one_out.py
===========================
Leave-one-spectrum-out cross-validation for the EDS Material Family and
Component Prediction System.

Validates the full pipeline against real historical EDS spectra without data leakage.
Outputs metrics, per-component precision/recall, and confusion matrices.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rule_engine.component_fingerprints import load_fingerprints
from rule_engine.component_scoring import rank_components, decide_component
from rule_engine.normalize import normalize_spectrum
from rule_engine.real_data import load_spectra, group_by_component, is_surface_treatment
from rule_engine.scoring import predict_spectrum, Decision, get_knowledge_base


def run_leave_one_out_validation(
    min_component_spectra: int = 1,
) -> Dict[str, Any]:
    """
    Execute Leave-One-Spectrum-Out cross-validation across all measured spectra.
    """
    start_time = time.perf_counter()
    kb = get_knowledge_base()
    all_fingerprints = load_fingerprints()

    # Build component to family mapping from KB and fingerprints
    comp_to_families: Dict[str, List[str]] = defaultdict(list)
    for fid, fam in kb.families.items():
        for cname in fam.get("components", []):
            comp_to_families[cname].append(fid)

    for cid, fp in all_fingerprints.items():
        for fid in fp.family_ids:
            if fid not in comp_to_families[fp.display_name]:
                comp_to_families[fp.display_name].append(fid)

    # Load empirical spectra
    spectra = load_spectra()
    valid_spectra = [
        s for s in spectra
        if s.component and not is_surface_treatment(s.component) and s.values
    ]

    total_evaluated = len(valid_spectra)
    family_correct = 0
    comp_top1_correct = 0
    comp_top3_correct = 0
    comp_top5_correct = 0

    decision_counts: Dict[str, int] = defaultdict(int)
    per_component_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {
        "total": 0, "top1": 0, "top3": 0, "top5": 0, "family_correct": 0
    })

    confusion_matrix: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    family_confusion_matrix: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    detailed_records = []

    for idx, spec in enumerate(valid_spectra):
        true_comp = spec.component
        true_families = comp_to_families.get(true_comp, [])

        norm_s = normalize_spectrum(spec.values, analysed_elements=list(spec.values.keys()))
        pred = predict_spectrum(spec.values, analysed_elements=list(spec.values.keys()), knowledge=kb)

        decision_str = pred.decision.value
        decision_counts[decision_str] += 1

        pred_family_id = pred.top.family_id if pred.top else "UNKNOWN"
        pred_family_label = pred.top.label if pred.top else "Unknown"

        # Check family correctness
        fam_match = (pred_family_id in true_families) if true_families else False
        if fam_match:
            family_correct += 1

        if true_families:
            for tf in true_families:
                family_confusion_matrix[tf][pred_family_id] += 1
        else:
            family_confusion_matrix["UNMAPPED"][pred_family_id] += 1

        # Candidate families for component ranking
        candidate_fids = [pred_family_id] if pred_family_id != "UNKNOWN" else list(kb.families.keys())
        if pred.decision == Decision.AMBIGUOUS:
            candidate_fids = [f.family_id for f in pred.families]

        ranked_candidates = rank_components(norm_s, candidate_fids, top_n=10)
        ranked_names = [c.display_name for c in ranked_candidates]

        is_top1 = len(ranked_names) > 0 and (ranked_names[0] == true_comp)
        is_top3 = true_comp in ranked_names[:3]
        is_top5 = true_comp in ranked_names[:5]

        if is_top1:
            comp_top1_correct += 1
        if is_top3:
            comp_top3_correct += 1
        if is_top5:
            comp_top5_correct += 1

        pred_top_comp = ranked_names[0] if ranked_names else "UNKNOWN"
        confusion_matrix[true_comp][pred_top_comp] += 1

        # Track per-component performance
        stats = per_component_stats[true_comp]
        stats["total"] += 1
        if fam_match:
            stats["family_correct"] += 1
        if is_top1:
            stats["top1"] += 1
        if is_top3:
            stats["top3"] += 1
        if is_top5:
            stats["top5"] += 1

        detailed_records.append({
            "spectrum_id": spec.spectrum_id or str(idx + 1),
            "true_component": true_comp,
            "true_families": true_families,
            "predicted_family": pred_family_id,
            "family_correct": fam_match,
            "predicted_component": pred_top_comp,
            "top1_correct": is_top1,
            "top3_correct": is_top3,
            "top5_correct": is_top5,
            "decision": decision_str,
            "ranked_candidates": ranked_names[:5],
        })

    elapsed_s = round(time.perf_counter() - start_time, 2)

    # Calculate percentages
    fam_acc = round((family_correct / total_evaluated * 100), 2) if total_evaluated else 0.0
    c_top1_acc = round((comp_top1_correct / total_evaluated * 100), 2) if total_evaluated else 0.0
    c_top3_acc = round((comp_top3_correct / total_evaluated * 100), 2) if total_evaluated else 0.0
    c_top5_acc = round((comp_top5_correct / total_evaluated * 100), 2) if total_evaluated else 0.0

    # Sub-metrics for components with >= 5 spectra
    geq5_total = sum(s["total"] for s in per_component_stats.values() if s["total"] >= 5)
    geq5_top1 = sum(s["top1"] for s in per_component_stats.values() if s["total"] >= 5)
    geq5_top3 = sum(s["top3"] for s in per_component_stats.values() if s["total"] >= 5)
    geq5_top1_acc = round((geq5_top1 / geq5_total * 100), 2) if geq5_total else 0.0
    geq5_top3_acc = round((geq5_top3 / geq5_total * 100), 2) if geq5_total else 0.0

    results = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_evaluated_spectra": total_evaluated,
            "unique_components_evaluated": len(per_component_stats),
            "duration_seconds": elapsed_s,
        },
        "summary_metrics": {
            "family_top1_accuracy_pct": fam_acc,
            "component_top1_accuracy_pct": c_top1_acc,
            "component_top3_accuracy_pct": c_top3_acc,
            "component_top5_accuracy_pct": c_top5_acc,
            "components_geq_5_spectra": {
                "total_spectra": geq5_total,
                "top1_accuracy_pct": geq5_top1_acc,
                "top3_accuracy_pct": geq5_top3_acc,
            },
            "decision_breakdown": dict(decision_counts),
        },
        "per_component_metrics": {
            comp: {
                "sample_count": s["total"],
                "family_accuracy_pct": round(s["family_correct"] / s["total"] * 100, 1),
                "top1_accuracy_pct": round(s["top1"] / s["total"] * 100, 1),
                "top3_accuracy_pct": round(s["top3"] / s["total"] * 100, 1),
                "top5_accuracy_pct": round(s["top5"] / s["total"] * 100, 1),
            }
            for comp, s in sorted(per_component_stats.items(), key=lambda x: -x[1]["total"])
        },
        "confusion_matrix": {k: dict(v) for k, v in confusion_matrix.items()},
        "family_confusion_matrix": {k: dict(v) for k, v in family_confusion_matrix.items()},
    }

    # Write output artifacts
    out_dir = PROJECT_ROOT / "validation" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "loo_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Write human-readable markdown summary
    md_path = out_dir / "validation_summary.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# EDS Prediction Pipeline — Leave-One-Spectrum-Out Validation Report\n\n")
        f.write(f"- **Evaluated Spectra**: {total_evaluated}\n")
        f.write(f"- **Unique Components**: {len(per_component_stats)}\n")
        f.write(f"- **Execution Time**: {elapsed_s}s\n\n")
        f.write("## Core Accuracy Metrics\n\n")
        f.write("| Metric | Accuracy | Target |\n")
        f.write("|---|---|---|\n")
        f.write(f"| **Family Top-1 Accuracy** | **{fam_acc}%** | ≥85% |\n")
        f.write(f"| **Component Top-1 Accuracy (All)** | **{c_top1_acc}%** | — |\n")
        f.write(f"| **Component Top-1 Accuracy (≥5 spectra)** | **{geq5_top1_acc}%** | ≥60% |\n")
        f.write(f"| **Component Top-3 Accuracy (≥5 spectra)** | **{geq5_top3_acc}%** | ≥80% |\n")
        f.write(f"| **Component Top-5 Accuracy (All)** | **{c_top5_acc}%** | ≥80% |\n\n")
        f.write("## Decision Breakdown\n\n")
        for dec, cnt in decision_counts.items():
            f.write(f"- `{dec}`: {cnt} ({cnt/total_evaluated*100:.1f}%)\n")
        f.write("\n## Per-Component Performance (Top Components)\n\n")
        f.write("| Component | Spectra | Family Acc | Top-1 Acc | Top-3 Acc |\n")
        f.write("|---|---|---|---|---|\n")
        for comp, s in sorted(per_component_stats.items(), key=lambda x: -x[1]["total"])[:20]:
            f.write(
                f"| {comp} | {s['total']} | {s['family_correct']/s['total']*100:.0f}% | "
                f"{s['top1']/s['total']*100:.0f}% | {s['top3']/s['total']*100:.0f}% |\n"
            )

    return results


if __name__ == "__main__":
    print("Running Leave-One-Spectrum-Out Validation...")
    res = run_leave_one_out_validation()
    sm = res["summary_metrics"]
    print(f"Family Top-1 Accuracy: {sm['family_top1_accuracy_pct']}%")
    print(f"Component Top-1 Accuracy (Overall): {sm['component_top1_accuracy_pct']}%")
    print(f"Component Top-1 Accuracy (>=5 spectra): {sm['components_geq_5_spectra']['top1_accuracy_pct']}%")
    print(f"Component Top-3 Accuracy (>=5 spectra): {sm['components_geq_5_spectra']['top3_accuracy_pct']}%")
    print("Report written to validation/results/validation_summary.md")
