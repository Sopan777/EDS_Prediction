"""
config.py
=========
Single place for every path, constant, and default setting shared across the
EDS pipeline (training, prediction, comparison). Change values here rather
than hunting through every script.
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
DEFAULT_DATA_FILE = DATA_DIR / "synthetic_eds_data.csv"  # .csv or .xlsx both supported

OUTPUTS_DIR = BASE_DIR / "outputs"

# --------------------------------------------------------------------------
# Data columns
# --------------------------------------------------------------------------

TARGET_COLUMN = "ComponentName"

# Row identifiers
ID_COLUMNS = ["Sr No.", "Spectrum", "Fe", "C", "O"]

def ensure_dirs() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# Rule Engine Configuration
# --------------------------------------------------------------------------

RULE_ENGINE = {
    "RULES_DIR": BASE_DIR / "rule_engine" / "rules",
    "RULES_FILE": BASE_DIR / "rule_engine" / "rules" / "rules.json",
    "RULE_CONFIDENCE_THRESHOLD": 0.40,
    "RULE_MIN_SUPPORT": 3,
    "RULE_ENGINE_VERSION": "1.0.0",
}

RULES_DIR = RULE_ENGINE["RULES_DIR"]
RULES_FILE = RULE_ENGINE["RULES_FILE"]
RULE_CONFIDENCE_THRESHOLD = RULE_ENGINE["RULE_CONFIDENCE_THRESHOLD"]
RULE_MIN_SUPPORT = RULE_ENGINE["RULE_MIN_SUPPORT"]
