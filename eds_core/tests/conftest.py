"""
tests/conftest.py
=================
Shared fixtures, plus quarantine of the legacy rule-engine suite.

Why the legacy suite is quarantined
-----------------------------------
The previous ``known_class_samples`` fixture built its sample set like this::

    result = engine.predict(features)
    if result.prediction == cls:
        samples[cls] = features

It kept a sample only when the engine ALREADY predicted it correctly, and the 36
``TestRegressionAllClasses`` tests then asserted that those samples predict
correctly. The fixture selected for exactly the property the tests verified, so
those tests could not fail - they reported 36 green regardless of the engine's
real behaviour.

Measured directly against the full dataset, the legacy engine scores 91.29%
overall but only 5.0% on Armature Bolt (5/100) and 5.2% on RLS Shim (5/97). The
suite showed none of that.

Rather than delete the files - they are the audit record of what the old engine
claimed - the legacy tests are skipped by default and the dishonest fixture is
repaired so it can never manufacture a pass again. Run them explicitly with::

    pytest --run-legacy

Two further reasons those tests should not gate the new engine: they exercise
``rule_engine/rules/rules.json``, which the approved plan retires as a decision
authority; and several of them pin chemically incorrect behaviour (Valve Piston
identified by 0.3% Ni rather than its V/W/Mo signature, Clamping Saddle by 2.5%
Cr rather than 81% Ni, and Blade Terminal - a Cu-Au contact - by 0.2% Si).

The current gate is ``tests/test_real_particles.py``, which scores the six real
analyst-labelled particles from the report PDFs.
"""

import csv
import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rule_engine.engine import RuleEngine
from rule_engine.preprocessing import FEATURE_COLUMNS, load_csv_data

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "synthetic_eds_data.csv"

#: Test modules that exercise the retired rule engine and the synthetic dataset.
LEGACY_MODULES = {
    "test_predictions.py",
    "test_preprocessing.py",
    "test_rule_engine.py",
    "test_validator.py",
    "test_integration.py",
}


def pytest_addoption(parser):
    parser.addoption(
        "--run-legacy",
        action="store_true",
        default=False,
        help="also run the legacy rule-engine tests (retired engine, "
        "synthetic dataset)",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-legacy"):
        return
    skip = pytest.mark.skip(
        reason="legacy rule-engine suite (retired engine + synthetic dataset); "
        "run with --run-legacy. See tests/conftest.py for why."
    )
    for item in items:
        if Path(str(item.fspath)).name in LEGACY_MODULES:
            item.add_marker(skip)


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
    """One sample per class: the FIRST row of each class, unconditionally.

    Deliberately does NOT check whether the engine predicts it correctly. The
    previous version did, which made every test built on this fixture
    self-fulfilling. Selecting samples by the property under test is not a
    weak test, it is a test that cannot fail.
    """
    feature_cols = FEATURE_COLUMNS

    with open(DATA_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

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
        samples[cls] = features

    return samples


@pytest.fixture(scope="session")
def all_class_names(csv_data):
    """Sorted list of all unique class names from the dataset."""
    from rule_engine.preprocessing import extract_target

    return sorted(set(extract_target(row).strip() for row in csv_data))
