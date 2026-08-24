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

SAVED_MODELS_DIR = BASE_DIR / "saved_models"
OUTPUTS_DIR = BASE_DIR / "outputs"

LABEL_ENCODER_PATH = SAVED_MODELS_DIR / "eds_label_encoder.pkl"
FEATURES_PATH = SAVED_MODELS_DIR / "eds_features.pkl"
BEST_MODEL_NAME_PATH = SAVED_MODELS_DIR / "eds_best_model_name.pkl"
CV_SUMMARY_PATH = SAVED_MODELS_DIR / "eds_cv_summary.csv"
ROBUSTNESS_SUMMARY_PATH = SAVED_MODELS_DIR / "eds_robustness_summary.csv"

# --------------------------------------------------------------------------
# Data columns
# --------------------------------------------------------------------------

TARGET_COLUMN = "ComponentName"

# Row identifiers - never used as model features (see notebook section 3).
ID_COLUMNS = ["Sr No.", "Spectrum", "Fe", "C", "O"]

# --------------------------------------------------------------------------
# Training defaults
# --------------------------------------------------------------------------

RANDOM_STATE = 42
TEST_SIZE = 0.20
N_SPLITS = 5  # stratified k-fold CV
NOISE_LEVELS_FOR_ROBUSTNESS_TEST = [0.0, 0.10, 0.25, 0.50, 1.00]

# --------------------------------------------------------------------------
# Inference defaults
# --------------------------------------------------------------------------

DEFAULT_TOP_K = 3
CONFIDENCE_THRESHOLD = 0.40  # below this, flag as "Unknown / needs review"

# Model registry key used when the user doesn't explicitly choose a model.
# Overridden at runtime by whatever eds_best_model_name.pkl says, if present.
DEFAULT_MODEL_KEY = "random_forest"

# --------------------------------------------------------------------------
# Noise injection defaults (used at *inference* time - see noise.py)
# --------------------------------------------------------------------------

# Master on/off switch for noise injection during prediction. Can also be
# toggled per-call via CLI flags / function arguments - this is just the
# fallback default.
NOISE_ENABLED_DEFAULT = False

# Noise std is expressed relative to each element's own within-class std,
# same convention as the notebook's robustness test (0.25 == "25% of the
# element's typical spread").
NOISE_LEVEL_DEFAULT = 0.25

# --------------------------------------------------------------------------
# Model registry
# --------------------------------------------------------------------------
# Human-readable name -> (module-key, pickle filename). Central source of
# truth used by train_all_models.py, predictor.py, and compare_models.py so
# every script agrees on what models exist and where they live on disk.

MODEL_REGISTRY = {
    "random_forest": {
        "display_name": "Random Forest",
        "pkl": SAVED_MODELS_DIR / "eds_model_random_forest.pkl",
    },
    "extra_trees": {
        "display_name": "Extra Trees",
        "pkl": SAVED_MODELS_DIR / "eds_model_extra_trees.pkl",
    },
    "catboost": {
        "display_name": "CatBoost",
        "pkl": SAVED_MODELS_DIR / "eds_model_catboost.pkl",
    },
    "xgboost": {
        "display_name": "XGBoost",
        "pkl": SAVED_MODELS_DIR / "eds_model_xgboost.pkl",
    },
}


def ensure_dirs() -> None:
    SAVED_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
