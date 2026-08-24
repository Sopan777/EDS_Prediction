"""
noise.py
========
Gaussian measurement-noise injection, factored out of the notebook's
robustness test (section 11) so the SAME logic can be reused in two places:

  1. train_all_models.py - the noise-robustness stress test during training
     (compare models across noise_level = 0%, 10%, 25%, 50%, 100%).
  2. predictor.py / eds_pipeline.py - an optional on/off toggle at
     *inference* time, so you can simulate "what would this model predict
     if this spectrum had X% more measurement noise" on real data.

Noise is Gaussian, scaled per-element relative to that element's own
within-class standard deviation in the training data (`col_std`) - the same
convention the notebook uses. This is a proxy for instrument noise, surface
contamination, or calibration drift, not a substitute for real noisy
measurements.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

import config


def compute_col_std(X_train: pd.DataFrame) -> pd.Series:
    """Per-column std of the training features, used to scale injected noise."""
    return X_train.std()


def inject_noise(
    X: pd.DataFrame,
    col_std: pd.Series,
    noise_level: float,
    enabled: bool = True,
    random_state: Optional[int] = None,
) -> pd.DataFrame:
    """
    Return a noisy copy of X. If `enabled` is False or `noise_level` is 0,
    returns an unmodified copy (the on/off switch the user asked for).

    noise_level: fraction of each column's own std to use as the injected
    noise's std (e.g. 0.25 -> noise ~ N(0, 0.25 * col_std)). Result is
    clipped at 0 since element weight% can't go negative.
    """
    X_noisy = X.copy()

    if not enabled or noise_level <= 0:
        return X_noisy

    rng = np.random.default_rng(random_state)
    for col in X_noisy.columns:
        std = col_std.get(col, 0.0)
        if std <= 0:
            continue
        noise = rng.normal(0, std * noise_level, size=len(X_noisy))
        X_noisy[col] = (X_noisy[col] + noise).clip(lower=0)

    return X_noisy


def inject_noise_single(
    feature_row: dict,
    col_std: pd.Series,
    noise_level: float = config.NOISE_LEVEL_DEFAULT,
    enabled: bool = config.NOISE_ENABLED_DEFAULT,
    random_state: Optional[int] = None,
) -> dict:
    """
    Same idea as inject_noise(), but convenient for a single {feature: value}
    prediction row instead of a whole DataFrame (used by predictor.py).
    """
    if not enabled or noise_level <= 0:
        return dict(feature_row)

    rng = np.random.default_rng(random_state)
    noisy = {}
    for feat, val in feature_row.items():
        std = col_std.get(feat, 0.0) if col_std is not None else 0.0
        if std and std > 0:
            val = val + rng.normal(0, std * noise_level)
        noisy[feat] = max(val, 0.0)
    return noisy
