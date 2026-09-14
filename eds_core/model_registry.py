"""
model_registry.py
==================
Maps a registry key ("random_forest", "extra_trees", "catboost", "xgboost")
to its model class. This is the ONE place that imports all four per-model
files, so train_all_models.py / predictor.py / compare_models.py just do:

    from model_registry import get_model_class, all_model_keys

and never need to know which file a given model lives in.
"""

from __future__ import annotations

from typing import Dict, List, Type

from models.base_model import BaseEDSModel
from models.random_forest_model import RandomForestEDSModel
from models.extra_trees_model import ExtraTreesEDSModel

_REGISTRY: Dict[str, Type[BaseEDSModel]] = {
    RandomForestEDSModel.key: RandomForestEDSModel,
    ExtraTreesEDSModel.key: ExtraTreesEDSModel,
}

# CatBoost / XGBoost are optional third-party dependencies (not part of
# scikit-learn). Import them lazily so that environments without one or both
# packages installed can still train/predict/compare with whichever models
# ARE available, instead of hard-crashing the whole pipeline on import.
try:
    from models.catboost_model import CatBoostEDSModel
    _REGISTRY[CatBoostEDSModel.key] = CatBoostEDSModel
except ImportError:
    print("[model_registry] catboost not installed - skipping CatBoost model "
          "(pip install catboost to enable it).")

try:
    from models.xgboost_model import XGBoostEDSModel
    _REGISTRY[XGBoostEDSModel.key] = XGBoostEDSModel
except ImportError:
    print("[model_registry] xgboost not installed - skipping XGBoost model "
          "(pip install xgboost to enable it).")


def all_model_keys() -> List[str]:
    return list(_REGISTRY.keys())


def get_model_class(key: str) -> Type[BaseEDSModel]:
    key = key.lower().replace(" ", "_").replace("-", "_")
    if key not in _REGISTRY:
        valid = ", ".join(_REGISTRY.keys())
        raise ValueError(f"Unknown model '{key}'. Choose one of: {valid}")
    return _REGISTRY[key]


def display_name_to_key(display_name: str) -> str:
    """e.g. 'Random Forest' -> 'random_forest' (matches notebook's naming)."""
    for key, cls in _REGISTRY.items():
        if cls.display_name == display_name:
            return key
    return display_name.lower().replace(" ", "_")
