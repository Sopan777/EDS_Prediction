"""
config.py
=========
Single place for every path, constant, and default setting shared across the
EDS pipeline (training, prediction, comparison). Change values here rather
than hunting through every script.

Environment variables override defaults where noted.
"""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
DEFAULT_DATA_FILE = DATA_DIR / "synthetic_eds_data.csv"  # .csv or .xlsx both supported
REPORTS_DIR = DATA_DIR / "reports"

FRONTEND_DIR = BASE_DIR / "frontend"
OUTPUTS_DIR = BASE_DIR / "outputs"

# Upload directory for file ingestion — configurable via UPLOADS_DIR env var
UPLOADS_DIR = Path(os.environ.get("UPLOADS_DIR", str(BASE_DIR / "uploads")))

# Database — configurable via DATABASE_URL env var (sqlite:///path or path)
_db_url = os.environ.get("DATABASE_URL", "")
if _db_url.startswith("sqlite:///"):
    DB_PATH = Path(_db_url[len("sqlite:///"):])
else:
    DB_PATH = BASE_DIR / "spectral_lab.db"

# --------------------------------------------------------------------------
# Data columns
# --------------------------------------------------------------------------

TARGET_COLUMN = "ComponentName"

# Row identifiers
ID_COLUMNS = ["Sr No.", "Spectrum", "Fe", "C", "O"]

def ensure_dirs() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


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
