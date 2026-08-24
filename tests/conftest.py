"""
tests/conftest.py
=================
Shared fixtures for the rule engine test suite.
Uses only pytest + stdlib (no pandas/numpy).
"""

import csv
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from rule_engine.engine import RuleEngine
from rule_engine.preprocessing import FEATURE_COLUMNS, load_csv_data


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "synthetic_eds_data.csv"


@pytest.fixture(scope="session")
def rule_engine():
    """Session-scoped RuleEngine instance (loaded once, shared across tests)."""
    return RuleEngine()


@pytest.fixture(scope="session")
def csv_data():
    """Load the full CSV dataset as list of row dicts."""
    return load_csv_data(DATA_PATH)


@pytest.fixture(scope="session")
def sample_data(csv_data):
    """A small subset of the CSV data - first 50 rows."""
    return csv_data[:50]


@pytest.fixture(scope="session")
def known_class_samples():
    """
    One known-correct sample per class that the rule engine correctly predicts.
    Dict of {class_name: {feature: value}} built from actual CSV data.
    """
    engine = RuleEngine()
    feature_cols = FEATURE_COLUMNS

    with open(DATA_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    samples = {}
    for row in rows:
        cls = row["ComponentName"].strip()
        if cls in samples:
            continue
        features = {}
        for col in feature_cols:
            val = row.get(col, "0")
            try:
                features[col] = float(val)
            except (ValueError, TypeError):
                features[col] = 0.0
        result = engine.predict(features)
        if result.prediction == cls:
            samples[cls] = features

    return samples


@pytest.fixture(scope="session")
def all_class_names(csv_data):
    """Sorted list of all unique class names from the dataset."""
    from rule_engine.preprocessing import extract_target
    classes = sorted(set(extract_target(row).strip() for row in csv_data))
    return classes
