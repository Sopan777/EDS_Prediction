"""
models/extra_trees_model.py
=============================
Extra Trees wrapper - hyperparameters carried over unchanged from the
notebook's make_models() (section 8).

Run this file directly to fit + save ONLY this model:

    python models/extra_trees_model.py
"""

from __future__ import annotations

from sklearn.ensemble import ExtraTreesClassifier

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))

from models.base_model import BaseEDSModel


class ExtraTreesEDSModel(BaseEDSModel):
    display_name = "Extra Trees"
    key = "extra_trees"

    def build(self):
        return ExtraTreesClassifier(
            n_estimators=500,
            max_features="sqrt",
            class_weight="balanced",
            random_state=self.random_state,
            n_jobs=-1,
        )


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

    model = ExtraTreesEDSModel(random_state=config.RANDOM_STATE, n_classes=len(encoder.classes_))
    model.fit(X_train, y_train, X_test, y_test)

    acc = (model.predict(X_test) == y_test).mean()
    print(f"{model.display_name} test accuracy: {acc:.4f}")

    config.ensure_dirs()
    model.save(config.MODEL_REGISTRY[model.key]["pkl"])
    print(f"Saved to {config.MODEL_REGISTRY[model.key]['pkl']}")
