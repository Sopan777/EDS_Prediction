"""
rule_engine/preprocessing.py
============================
Pure-stdlib CSV data loading, feature extraction, and input validation.
Mirrors the logic of data_utils.py but uses only csv, statistics, and
other stdlib modules instead of pandas/numpy.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Feature columns used by the rule engine (excludes ID columns and constant columns)
# ID columns: Sr No., Spectrum, Fe, C, O
# Constant column: Cl (all zeros)
FEATURE_COLUMNS = [
    "Al", "Si", "P", "S", "Cr", "Mn", "Ni", "Pb",
    "Mo", "Cu", "Sn", "Zn", "Au", "K", "N", "Ca", "V", "W",
]

ID_COLUMNS = {"Sr No.", "Spectrum", "Fe", "C", "O"}
CONSTANT_COLUMNS = {"Cl"}
TARGET_COLUMN = "ComponentName"


def load_csv_data(file_path: str | Path) -> List[Dict[str, Any]]:
    """
    Load CSV data into a list of row dicts.

    Returns list of dicts with keys for all columns.
    Non-numeric feature values are converted to 0.0.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Data file not found: {file_path}")

    rows = []
    with open(file_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed = {}
            for key, value in row.items():
                if key == TARGET_COLUMN:
                    parsed[key] = value.strip() if value else ""
                elif key in ID_COLUMNS or key in CONSTANT_COLUMNS:
                    parsed[key] = value
                else:
                    # Feature column - convert to float
                    parsed[key] = _safe_float(value)
            rows.append(parsed)
    return rows


def extract_features(row: Dict[str, Any]) -> Dict[str, float]:
    """Extract only the feature columns from a data row as floats."""
    return {col: float(row.get(col, 0.0)) for col in FEATURE_COLUMNS}


def extract_target(row: Dict[str, Any]) -> str:
    """Extract the target column value from a data row."""
    return str(row.get(TARGET_COLUMN, ""))


def validate_input(eds_values: Dict[str, Any]) -> Dict[str, float]:
    """
    Validate and normalize prediction input.

    Accepts a dict of {element: value} and returns a normalized dict
    with all FEATURE_COLUMNS present (missing ones default to 0.0).
    Non-numeric values are converted to 0.0.
    """
    normalized = {}
    for col in FEATURE_COLUMNS:
        val = eds_values.get(col, 0.0)
        normalized[col] = _safe_float(val)
    return normalized


def stratified_split(
    data: List[Dict[str, Any]],
    train_ratio: float = 0.80,
    val_ratio: float = 0.10,
    test_ratio: float = 0.10,
    random_seed: int = 42,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Split data into train/validation/test sets with stratification by target.

    Uses stdlib random module for reproducibility.
    """
    import random

    rng = random.Random(random_seed)

    # Group by class
    class_groups: Dict[str, List[Dict[str, Any]]] = {}
    for row in data:
        target = extract_target(row)
        if target not in class_groups:
            class_groups[target] = []
        class_groups[target].append(row)

    train_set: List[Dict[str, Any]] = []
    val_set: List[Dict[str, Any]] = []
    test_set: List[Dict[str, Any]] = []

    for class_name in sorted(class_groups.keys()):
        samples = class_groups[class_name][:]
        rng.shuffle(samples)

        n = len(samples)
        n_train = max(1, int(n * train_ratio))
        n_val = max(1, int(n * val_ratio))
        # Rest goes to test
        n_test = n - n_train - n_val

        train_set.extend(samples[:n_train])
        val_set.extend(samples[n_train:n_train + n_val])
        test_set.extend(samples[n_train + n_val:])

    return train_set, val_set, test_set


def compute_feature_stats(
    data: List[Dict[str, Any]],
    class_name: str,
) -> Dict[str, Dict[str, float]]:
    """
    Compute per-feature statistics (min, max, mean, std) for a given class.

    Returns dict of {feature_name: {min, max, mean, std, nonzero_count, total_count}}.
    """
    # Collect values per feature for the target class
    feature_values: Dict[str, List[float]] = {col: [] for col in FEATURE_COLUMNS}

    for row in data:
        if extract_target(row) == class_name:
            for col in FEATURE_COLUMNS:
                feature_values[col].append(_safe_float(row.get(col, 0.0)))

    stats: Dict[str, Dict[str, float]] = {}
    for col, values in feature_values.items():
        if not values:
            stats[col] = {"min": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0,
                          "nonzero_count": 0, "total_count": 0}
            continue

        n = len(values)
        mean_val = sum(values) / n
        variance = sum((v - mean_val) ** 2 for v in values) / n if n > 1 else 0.0
        std_val = variance ** 0.5

        stats[col] = {
            "min": min(values),
            "max": max(values),
            "mean": mean_val,
            "std": std_val,
            "nonzero_count": sum(1 for v in values if v != 0.0),
            "total_count": n,
        }

    return stats


def _safe_float(value: Any) -> float:
    """Safely convert a value to float. Returns 0.0 for non-numeric values."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        value = value.strip()
        if not value or value in ("-", "N/A", "n/a", "NA", ""):
            return 0.0
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0
