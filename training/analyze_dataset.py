"""
training/analyze_dataset.py
============================
Pure-stdlib script that reads the CSV data, profiles it, and outputs
an analysis report as JSON to outputs/dataset_analysis.json.

Usage:
    python training/analyze_dataset.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rule_engine.preprocessing import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    load_csv_data,
    extract_features,
    extract_target,
    compute_feature_stats,
)


def analyze_dataset(data_path: str | Path) -> dict:
    """
    Perform comprehensive dataset analysis.

    Returns a dict with:
        - shape: (rows, cols)
        - class_distribution: {class_name: count}
        - feature_stats: per-class feature statistics
        - discriminating_features: features that uniquely identify classes
        - global_feature_stats: overall feature ranges
    """
    data = load_csv_data(data_path)

    # Basic shape info
    n_rows = len(data)
    n_features = len(FEATURE_COLUMNS)

    # Class distribution
    class_dist: dict = {}
    for row in data:
        target = extract_target(row)
        class_dist[target] = class_dist.get(target, 0) + 1

    # Per-class feature stats
    class_feature_stats: dict = {}
    all_classes = sorted(class_dist.keys())
    for cls in all_classes:
        class_feature_stats[cls] = compute_feature_stats(data, cls)

    # Global feature stats
    global_stats: dict = {}
    for col in FEATURE_COLUMNS:
        values = [float(row.get(col, 0.0)) for row in data]
        n = len(values)
        mean_val = sum(values) / n if n > 0 else 0.0
        global_stats[col] = {
            "min": min(values) if values else 0.0,
            "max": max(values) if values else 0.0,
            "mean": mean_val,
            "nonzero_ratio": sum(1 for v in values if v != 0.0) / n if n > 0 else 0.0,
        }

    # Identify discriminating features (features that are non-zero only for specific classes)
    discriminators: dict = {}
    for col in FEATURE_COLUMNS:
        classes_with_nonzero = []
        for cls in all_classes:
            stats = class_feature_stats[cls][col]
            if stats["nonzero_count"] > 0:
                classes_with_nonzero.append(cls)

        if 0 < len(classes_with_nonzero) <= 4:
            discriminators[col] = classes_with_nonzero

    # Duplicate detection
    feature_rows = []
    for row in data:
        feat = extract_features(row)
        feature_rows.append(tuple(sorted(feat.items())))
    n_duplicates = n_rows - len(set(feature_rows))

    # Missing values check
    n_missing = 0
    for row in data:
        for col in FEATURE_COLUMNS:
            val = row.get(col)
            if val is None or (isinstance(val, str) and val.strip() == ""):
                n_missing += 1

    report = {
        "shape": {"rows": n_rows, "features": n_features},
        "n_classes": len(all_classes),
        "classes": all_classes,
        "class_distribution": dict(sorted(class_dist.items())),
        "feature_columns": FEATURE_COLUMNS,
        "global_feature_stats": global_stats,
        "discriminating_features": discriminators,
        "n_duplicate_feature_rows": n_duplicates,
        "n_missing_values": n_missing,
        "class_feature_stats": class_feature_stats,
    }

    return report


def main():
    """Run dataset analysis and save report."""
    project_root = Path(__file__).resolve().parent.parent
    data_path = project_root / "data" / "synthetic_eds_data.csv"
    output_dir = project_root / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Analyzing dataset: {data_path}")
    report = analyze_dataset(data_path)

    output_path = output_dir / "dataset_analysis.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nDataset Analysis Report")
    print(f"{'='*50}")
    print(f"Rows: {report['shape']['rows']}")
    print(f"Features: {report['shape']['features']}")
    print(f"Classes: {report['n_classes']}")
    print(f"Duplicate feature rows: {report['n_duplicate_feature_rows']}")
    print(f"Missing values: {report['n_missing_values']}")
    print(f"\nDiscriminating features:")
    for feat, classes in report["discriminating_features"].items():
        print(f"  {feat}: only in {classes}")
    print(f"\nReport saved to: {output_path}")


if __name__ == "__main__":
    main()
