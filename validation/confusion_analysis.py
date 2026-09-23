"""
validation/confusion_analysis.py
================================
Identifies hard component pairs and analyzes why components are confused
(same family, overlapping chemistry, small sample counts).
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rule_engine.component_fingerprints import load_fingerprints
from rule_engine.scoring import get_knowledge_base


def analyze_confusion(loo_results_path: Optional[Path] = None) -> Dict[str, Any]:
    """Analyze confusion matrix from leave-one-out validation results."""
    p = loo_results_path or (PROJECT_ROOT / "validation" / "results" / "loo_results.json")
    if not p.exists():
        raise FileNotFoundError(f"LOO results not found at {p}. Run leave_one_out.py first.")

    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    cm = data.get("confusion_matrix", {})
    all_fingerprints = load_fingerprints()
    kb = get_knowledge_base()

    # Component -> Family lookup
    comp_families = {}
    for cid, fp in all_fingerprints.items():
        comp_families[fp.display_name] = fp.family_ids

    confused_pairs = []

    for true_comp, preds in cm.items():
        for pred_comp, count in preds.items():
            if true_comp == pred_comp:
                continue
            if count <= 0:
                continue

            true_fams = comp_families.get(true_comp, [])
            pred_fams = comp_families.get(pred_comp, [])
            same_family = bool(set(true_fams).intersection(set(pred_fams)))

            true_fp = next((fp for fp in all_fingerprints.values() if fp.display_name == true_comp), None)
            pred_fp = next((fp for fp in all_fingerprints.values() if fp.display_name == pred_comp), None)

            true_n = true_fp.sample_count if true_fp else 0
            pred_n = pred_fp.sample_count if pred_fp else 0

            # Determine likely cause
            causes = []
            if same_family:
                causes.append("Identical metallurgical family (isochemical alloy variant)")
            else:
                causes.append("Cross-family boundary confusion")

            if true_n < 5 or pred_n < 5:
                causes.append(f"Small sample count (True: n={true_n}, Pred: n={pred_n})")

            confused_pairs.append({
                "true_component": true_comp,
                "predicted_component": pred_comp,
                "misclassification_count": count,
                "same_family": same_family,
                "true_families": true_fams,
                "predicted_families": pred_fams,
                "true_sample_count": true_n,
                "pred_sample_count": pred_n,
                "primary_cause": "; ".join(causes),
            })

    # Sort by misclassification count descending
    confused_pairs.sort(key=lambda x: -x["misclassification_count"])

    out_dir = PROJECT_ROOT / "validation" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    result_data = {
        "total_confused_pairs": len(confused_pairs),
        "hard_component_pairs": confused_pairs,
    }

    with open(out_dir / "hard_component_pairs.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, indent=2)

    # Write markdown summary
    with open(out_dir / "hard_component_pairs.md", "w", encoding="utf-8") as f:
        f.write("# Hard Component Pairs Analysis\n\n")
        f.write("Components frequently confused during empirical Leave-One-Spectrum-Out cross-validation:\n\n")
        f.write("| True Component | Misclassified As | Errors | Same Family? | Diagnostic Cause |\n")
        f.write("|---|---|---|---|---|\n")
        for cp in confused_pairs[:25]:
            sf_str = "Yes" if cp["same_family"] else "**No (Cross-Family)**"
            f.write(
                f"| {cp['true_component']} | {cp['predicted_component']} | "
                f"{cp['misclassification_count']} | {sf_str} | {cp['primary_cause']} |\n"
            )

    return result_data


if __name__ == "__main__":
    res = analyze_confusion()
    print(f"Identified {res['total_confused_pairs']} confused component pairs.")
    print("Report written to validation/results/hard_component_pairs.md")
