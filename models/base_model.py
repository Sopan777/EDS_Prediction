"""
models/base_model.py
=====================
Common interface every per-model file implements. Keeping this thin (just
build/fit/predict/predict_proba/save/load) is what lets train_all_models.py,
predictor.py, and compare_models.py treat "Random Forest", "Extra Trees",
"CatBoost", and "XGBoost" completely interchangeably.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd


class BaseEDSModel(ABC):
    """Abstract wrapper around one sklearn/XGBoost/CatBoost estimator."""

    #: Human-readable name, exactly matching the notebook's make_models() keys.
    display_name: str = "Base Model"

    #: registry key, e.g. "random_forest" - used for filenames / CLI --model flag.
    key: str = "base"

    def __init__(self, random_state: int = 42, n_classes: Optional[int] = None):
        self.random_state = random_state
        self.n_classes = n_classes
        self.model = self.build()

    @abstractmethod
    def build(self):
        """Return a fresh, UNFITTED estimator instance (needed for CV folds)."""
        raise NotImplementedError

    def fit(self, X_train, y_train, X_val=None, y_val=None, verbose: bool = False):
        """
        Fit self.model. X_val/y_val are accepted (and used, where the
        underlying library supports it) so CatBoost/XGBoost can track an
        eval set during training, matching the notebook's section 10.
        """
        self.model.fit(X_train, y_train)
        return self

    def predict(self, X):
        return self.model.predict(X)

    def predict_proba(self, X):
        return self.model.predict_proba(X)

    @property
    def feature_importances_(self):
        return getattr(self.model, "feature_importances_", None)

    def save(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, path)

    def load(self, path: str | Path):
        self.model = joblib.load(path)
        return self

    def __repr__(self):
        return f"<{self.__class__.__name__} '{self.display_name}'>"
