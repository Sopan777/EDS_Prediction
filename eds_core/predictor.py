"""
predictor.py
============
Inference layer - notebook sections 16-17, generalised to:

  - load ANY registered model on demand (not just the "best" one), cached
    per-key so repeat calls don't hit disk again
  - an on/off noise-injection toggle applied to the input before predicting,
    for simulating measurement noise on a real spectrum (see noise.py)
  - a confidence-threshold "Unknown / needs review" flag, same as v1/v2

This module has no CLI of its own - it's imported by eds_pipeline.py (the
combined extract+predict pipeline) and compare_models.py (side-by-side
comparison). Run predictor.py directly for a couple of quick smoke-test
predictions using the notebook's example spectra.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

import config
import data_utils
import noise as noise_mod
from model_registry import get_model_class

# --------------------------------------------------------------------------
# Cached artifacts - loaded once per process, reused across calls.
# --------------------------------------------------------------------------

_ENCODER = None
_FEATURES: Optional[List[str]] = None
_COL_STD: Optional[pd.Series] = None
_MODEL_CACHE: Dict[str, object] = {}
_BEST_MODEL_KEY: Optional[str] = None


def _load_shared_artifacts():
    global _ENCODER, _FEATURES, _COL_STD, _BEST_MODEL_KEY
    if _ENCODER is None:
        if not config.LABEL_ENCODER_PATH.exists():
            raise FileNotFoundError(
                "No trained artifacts found. Run `python train_all_models.py` first."
            )
        _ENCODER = joblib.load(config.LABEL_ENCODER_PATH)
    if _FEATURES is None:
        _FEATURES = joblib.load(config.FEATURES_PATH)
    if _COL_STD is None:
        # Recompute training-feature std for noise scaling. Cheap and keeps
        # predictor.py self-contained without needing to pickle a Series.
        df = data_utils.load_raw_data()
        X, _, _ = data_utils.build_feature_matrix(df)
        _COL_STD = X[_FEATURES].std()
    if _BEST_MODEL_KEY is None and config.BEST_MODEL_NAME_PATH.exists():
        best_display_name = joblib.load(config.BEST_MODEL_NAME_PATH)
        from model_registry import display_name_to_key
        _BEST_MODEL_KEY = display_name_to_key(best_display_name)


def default_model_key() -> str:
    """The most noise-robust model chosen by train_all_models.py, if
    available; otherwise config.DEFAULT_MODEL_KEY."""
    _load_shared_artifacts()
    return _BEST_MODEL_KEY or config.DEFAULT_MODEL_KEY


def get_model(model_key: str):
    """Load (and cache) one trained model by registry key, e.g. 'catboost'."""
    _load_shared_artifacts()
    model_key = model_key.lower().replace(" ", "_").replace("-", "_")
    if model_key in _MODEL_CACHE:
        return _MODEL_CACHE[model_key]

    model_cls = get_model_class(model_key)  # validates the key
    pkl_path = config.MODEL_REGISTRY[model_key]["pkl"]
    if not pkl_path.exists():
        raise FileNotFoundError(
            f"No saved model at {pkl_path}. Run `python train_all_models.py` "
            f"(or `python models/{model_key}_model.py`) first."
        )
    instance = model_cls.__new__(model_cls)  # skip build(); we're loading, not fitting
    instance.random_state = config.RANDOM_STATE
    instance.n_classes = None
    instance.model = joblib.load(pkl_path)
    _MODEL_CACHE[model_key] = instance
    return instance


def predict_component(
    eds_values: dict,
    model_key: Optional[str] = None,
    top_k: int = config.DEFAULT_TOP_K,
    confidence_threshold: float = config.CONFIDENCE_THRESHOLD,
    noise_enabled: bool = config.NOISE_ENABLED_DEFAULT,
    noise_level: float = config.NOISE_LEVEL_DEFAULT,
    noise_random_state: Optional[int] = None,
) -> pd.DataFrame:
    """
    Predict the top-k most likely component(s) for one spectrum.

    eds_values: dict of {element: weight_percent} - e.g. straight from
        eds_extractor's per-spectrum "values", or hand-typed. Missing
        elements are treated as 0, same convention as training.
    model_key: which registered model to use ("random_forest", "extra_trees",
        "catboost", "xgboost"). Defaults to the most noise-robust model
        selected by train_all_models.py.
    noise_enabled / noise_level: the on/off noise-injection toggle. When
        enabled, Gaussian noise (scaled to noise_level * each element's
        training std) is added to the input BEFORE prediction, to simulate
        measurement noise. Off by default - real extracted spectra should
        normally be predicted on as-is.

    Returns a DataFrame with columns [Component, Probability], plus
    `.attrs["flag"]` set when the top prediction is below the confidence
    threshold.
    """
    _load_shared_artifacts()
    model_key = model_key or default_model_key()
    model = get_model(model_key)

    feature_row = data_utils.eds_values_to_feature_row(eds_values, _FEATURES)

    if noise_enabled:
        feature_row = noise_mod.inject_noise_single(
            feature_row, _COL_STD, noise_level=noise_level,
            enabled=True, random_state=noise_random_state,
        )

    input_df = pd.DataFrame([feature_row])[_FEATURES]

    probabilities = np.asarray(model.predict_proba(input_df))[0]
    top_indices = np.argsort(probabilities)[::-1][:top_k]

    predictions = []
    for index in top_indices:
        predictions.append({
            "Component": _ENCODER.inverse_transform([index])[0],
            "Probability": probabilities[index],
        })

    result = pd.DataFrame(predictions)
    result.attrs["model_key"] = model_key
    result.attrs["model_display_name"] = model.display_name
    result.attrs["noise_enabled"] = noise_enabled
    result.attrs["noise_level"] = noise_level if noise_enabled else 0.0
    if result["Probability"].iloc[0] < confidence_threshold:
        result.attrs["flag"] = "LOW CONFIDENCE — treat as Unknown / needs manual review"
    return result


def predict_components_batch(
    spectra: List[dict],
    model_key: Optional[str] = None,
    top_k: int = config.DEFAULT_TOP_K,
    confidence_threshold: float = config.CONFIDENCE_THRESHOLD,
    noise_enabled: bool = config.NOISE_ENABLED_DEFAULT,
    noise_level: float = config.NOISE_LEVEL_DEFAULT,
    noise_random_state: Optional[int] = None,
) -> List[pd.DataFrame]:
    """Same as predict_component(), applied to a list of {element: value}
    dicts - e.g. every spectrum row extracted from one EDS table. Returns
    one result DataFrame per spectrum, in the same order."""
    return [
        predict_component(
            values, model_key=model_key, top_k=top_k,
            confidence_threshold=confidence_threshold,
            noise_enabled=noise_enabled, noise_level=noise_level,
            noise_random_state=noise_random_state,
        )
        for values in spectra
    ]


if __name__ == "__main__":
    new_eds = {
        "C": 0.2, "O": 0.1, "Al": 0.0, "Si": 0.5, "P": 0.02, "S": 0.01,
        "Cr": 12.5, "Mn": 0.8, "Ni": 8.2, "Pb": 0.0, "Fe": 76.0, "Mo": 1.2,
        "Cu": 0.2, "Sn": 0.0, "Zn": 0.0, "Au": 0.0, "K": 0.0, "N": 0.0,
        "Ca": 0.0, "V": 0.0, "W": 0.0,
    }
    ambiguous_eds = {
        "C": 15.0, "O": 5.0, "Al": 0.0, "Si": 0.2, "P": 0.0, "S": 0.0,
        "Cr": 1.0, "Mn": 0.5, "Ni": 0.5, "Pb": 0.0, "Fe": 40.0, "Mo": 0.0,
        "Cu": 20.0, "Sn": 2.0, "Zn": 1.0, "Au": 0.0, "K": 0.0, "N": 0.0,
        "Ca": 0.0, "V": 0.0, "W": 0.0,
    }

    for label, sample in [("Clear-cut sample", new_eds), ("Ambiguous sample", ambiguous_eds)]:
        print(f"\n=== {label} (model: {default_model_key()}, noise: off) ===")
        result = predict_component(sample)
        print(result)
        if "flag" in result.attrs:
            print("⚠️", result.attrs["flag"])
