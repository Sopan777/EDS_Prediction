"""
data_utils.py
=============
Data loading and preprocessing shared by the training script and (indirectly)
by inference. Mirrors notebook sections 1-4 exactly:

  1. Load data (CSV or XLSX)
  2. Basic data check
  3. Remove columns that should not be used as features (row identifiers)
  4. Remove constant features

Keeping this in one place means train_all_models.py and any future
retraining script can't silently drift out of sync with each other on how
the raw file gets turned into X / y.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import pandas as pd

import config


def load_raw_data(file_path: str | Path = config.DEFAULT_DATA_FILE) -> pd.DataFrame:
    """Load the raw EDS dataset from .csv or .xlsx, whichever is given."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Data file not found: {file_path}")

    if file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path)
    elif file_path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported data file type: {file_path.suffix}")

    return df


def basic_data_check(df: pd.DataFrame) -> None:
    """Print the same sanity-check summary as notebook section 2."""
    print("Dataset shape:", df.shape)
    print("\nMissing values:", int(df.isnull().sum().sum()), "total missing cells")
    print("Duplicate rows:", int(df.duplicated().sum()))
    print("\nTarget distribution:")
    print(df[config.TARGET_COLUMN].value_counts())


def build_feature_matrix(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """
    Reproduce notebook sections 3-4:
      - drop row-identifier columns and the target from the feature matrix
      - drop any constant columns (zero variance -> no signal, just noise
        for the model, and can break some scalers/splitters downstream)

    Returns (X, y, dropped_constant_columns).
    """
    target = config.TARGET_COLUMN
    drop_cols = [c for c in config.ID_COLUMNS if c in df.columns]

    X = df.drop(columns=[target] + drop_cols)
    y = df[target]

    constant_columns = [col for col in X.columns if X[col].nunique(dropna=False) <= 1]
    if constant_columns:
        X = X.drop(columns=constant_columns)

    return X, y, constant_columns


def eds_values_to_feature_row(eds_values: dict, feature_columns: List[str]) -> dict:
    """
    Map a raw {element: value} dict (e.g. from eds_extractor's per-spectrum
    "values", or a hand-typed dict) onto the exact feature columns the model
    was trained on:
      - missing elements -> 0.0
      - None / non-numeric placeholder cells (e.g. "-", "N/A") -> 0.0
      - extra elements not seen during training are dropped
    Never fabricates a *measured* value - this only fills in "not reported"
    as zero weight%, which is the same convention the training data itself
    uses for elements absent from a given spectrum.
    """
    row = {}
    for feat in feature_columns:
        val = eds_values.get(feat, 0.0)
        if val is None:
            val = 0.0
        elif isinstance(val, str):
            # Placeholder text like "-" or "N/A" from the extractor -> 0.0
            try:
                val = float(val)
            except ValueError:
                val = 0.0
        row[feat] = float(val)
    return row
