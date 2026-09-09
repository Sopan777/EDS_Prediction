"""
models package
===============
Each model gets its own file (random_forest_model.py, extra_trees_model.py,
catboost_model.py, xgboost_model.py) wrapping one estimator behind the same
small interface defined in base_model.py:

    build()               -> a fresh, unfitted estimator (needed for CV,
                              which must fit a new model per fold)
    fit(X, y, ...)         -> fit self.model, returns self
    predict(X)              -> class-index predictions
    predict_proba(X)        -> class probabilities
    save(path) / load(path) -> joblib persistence

model_registry.py ties the display name used throughout the notebook
("Random Forest", "CatBoost", ...) to these classes, so training,
prediction, and comparison scripts all select models the same way.
"""
