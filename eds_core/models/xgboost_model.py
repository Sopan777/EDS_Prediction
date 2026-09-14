"""
models/xgboost_model.py
=========================
XGBoost wrapper - hyperparameters carried over unchanged from the notebook's
make_models() (section 8). Overrides fit() to pass an eval_set, matching
notebook section 10 (trained_models loop).

Run this file directly to fit + save ONLY this model:

    python models/xgboost_model.py
"""

from __future__ import annotations

from xgboost import XGBClassifier

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))

from models.base_model import BaseEDSModel


class XGBoostEDSModel(BaseEDSModel):
    display_name = "XGBoost"
    key = "xgboost"

    def build(self):
        return XGBClassifier(
            n_estimators=600,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="multi:softprob",
            num_class=self.n_classes,
            eval_metric="mlogloss",
            random_state=self.random_state,
            n_jobs=-1,
            tree_method="hist",
        )

    def fit(self, X_train, y_train, X_val=None, y_val=None, verbose: bool = False):
        if X_val is not None and y_val is not None:
            self.model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=verbose)
        else:
            self.model.fit(X_train, y_train)
        return self


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config
    import data_utils
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import LabelEncoder

    df = data_utils.load_raw_data()
    X, y, _ = data_utils.build_feature_matrix(df)
    encoder = LabelEncoder()
    y_enc = encoder.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=config.TEST_SIZE, random_state=config.RANDOM_STATE,
        shuffle=True, stratify=y_enc,
    )

    model = XGBoostEDSModel(random_state=config.RANDOM_STATE, n_classes=len(encoder.classes_))
    model.fit(X_train, y_train, X_test, y_test)

    acc = (model.predict(X_test).reshape(-1) == y_test).mean()
    print(f"{model.display_name} test accuracy: {acc:.4f}")

    config.ensure_dirs()
    model.save(config.MODEL_REGISTRY[model.key]["pkl"])
    print(f"Saved to {config.MODEL_REGISTRY[model.key]['pkl']}")
