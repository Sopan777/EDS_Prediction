"""
train_all_models.py
====================
Full implementation of the EDS_Component_Prediction_v2 notebook as a
runnable script - every section, in order:

  1.  Load data
  2.  Basic data check
  3.  Remove non-feature (row identifier) columns
  4.  Remove constant features
  5.  Separability sanity check (coefficient of variation)
  6.  Encode target
  7.  Train/test split
  8.  Model definitions (see models/*.py)
  9.  Stratified k-fold cross-validation (model comparison)
  10. Train final models on the train/test split
  11. Noise-robustness stress test (the key comparison - see noise.py)
  12. Detailed classification report for the best (most noise-robust) model
  13. Confusion matrices - clean vs. moderately noisy test data
  14. Feature importance
  15. Save all models + label encoder + feature list + best model name

Plots are saved as PNG files under outputs/ instead of plt.show(), since
this runs headless as a script.

Usage:
    python train_all_models.py [--data path/to/file.csv] [--no-plots]
"""

from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd

import config
import data_utils
import noise as noise_mod
from model_registry import all_model_keys, get_model_class

from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    top_k_accuracy_score,
    classification_report,
    confusion_matrix,
)


def make_models(n_classes: int, random_state: int = config.RANDOM_STATE):
    """Factory: a fresh, unfitted instance of every registered model.
    Mirrors the notebook's make_models() (section 8) - needed fresh every
    CV fold so folds never share fitted state."""
    return {
        get_model_class(key).display_name: get_model_class(key)(
            random_state=random_state, n_classes=n_classes
        )
        for key in all_model_keys()
    }


def section(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def run(data_path=None, make_plots: bool = True):
    config.ensure_dirs()
    data_path = data_path or config.DEFAULT_DATA_FILE

    # ---- 1. Load data -----------------------------------------------------
    section("1. Load data")
    df = data_utils.load_raw_data(data_path)
    print("Dataset shape:", df.shape)
    print("Columns:", df.columns.tolist())

    # ---- 2. Basic data check ----------------------------------------------
    section("2. Basic data check")
    data_utils.basic_data_check(df)

    # ---- 3 & 4. Feature matrix (drop IDs + constant columns) --------------
    section("3-4. Build feature matrix (drop IDs + constant columns)")
    X, y, constant_columns = data_utils.build_feature_matrix(df)
    print("Constant columns (dropped):", constant_columns)
    print("Final features:", X.columns.tolist())

    # ---- 5. Separability sanity check --------------------------------------
    section("5. Sanity check: how separable are these classes actually?")
    numeric_columns = X.columns.tolist()
    summary_rows = []
    for name, sub in df.groupby(config.TARGET_COLUMN):
        dominant = sub[numeric_columns].mean().sort_values(ascending=False).head(1)
        el = dominant.index[0]
        mean_val = sub[el].mean()
        std_val = sub[el].std()
        cv = std_val / mean_val if mean_val > 0 else np.nan
        summary_rows.append({"Component": name, "Dominant Element": el,
                              "Mean": mean_val, "Std": std_val, "CoeffOfVariation": cv})
    sep_df = pd.DataFrame(summary_rows).sort_values("CoeffOfVariation")
    print("Median coefficient of variation across classes' dominant element:",
          round(sep_df["CoeffOfVariation"].median(), 4))
    print(sep_df.head(10).to_string(index=False))

    # ---- 6. Encode target ---------------------------------------------------
    section("6. Encode target")
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    class_names = label_encoder.classes_
    n_classes = len(class_names)
    print("Number of classes:", n_classes)

    # ---- 7. Train/test split -------------------------------------------------
    section("7. Train/test split")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=config.TEST_SIZE, random_state=config.RANDOM_STATE,
        shuffle=True, stratify=y_encoded,
    )
    print("Train:", X_train.shape, " Test:", X_test.shape)

    # ---- 8. Model definitions -------------------------------------------------
    section("8. Model definitions")
    print("Models:", list(make_models(n_classes).keys()))

    # ---- 9. Stratified k-fold cross-validation --------------------------------
    section("9. Stratified k-fold cross-validation")
    skf = StratifiedKFold(n_splits=config.N_SPLITS, shuffle=True, random_state=config.RANDOM_STATE)
    cv_scores = {name: {"Accuracy": [], "Macro F1": [], "Top-3 Accuracy": []}
                 for name in make_models(n_classes)}

    t0 = time.time()
    for fold, (tr_idx, te_idx) in enumerate(skf.split(X, y_encoded)):
        Xtr, Xte = X.iloc[tr_idx], X.iloc[te_idx]
        ytr, yte = y_encoded[tr_idx], y_encoded[te_idx]

        for name, model in make_models(n_classes).items():
            model.fit(Xtr, ytr)
            pred = np.asarray(model.predict(Xte)).reshape(-1)
            proba = model.predict_proba(Xte)

            cv_scores[name]["Accuracy"].append(accuracy_score(yte, pred))
            cv_scores[name]["Macro F1"].append(f1_score(yte, pred, average="macro", zero_division=0))
            cv_scores[name]["Top-3 Accuracy"].append(
                top_k_accuracy_score(yte, proba, k=3, labels=np.arange(n_classes))
            )
        print(f"fold {fold + 1}/{config.N_SPLITS} done")

    print(f"\nCV finished in {time.time() - t0:.1f}s")

    cv_summary = pd.DataFrame({
        name: {
            "Accuracy (mean)": np.mean(m["Accuracy"]), "Accuracy (std)": np.std(m["Accuracy"]),
            "Macro F1 (mean)": np.mean(m["Macro F1"]), "Macro F1 (std)": np.std(m["Macro F1"]),
            "Top-3 Acc (mean)": np.mean(m["Top-3 Accuracy"]), "Top-3 Acc (std)": np.std(m["Top-3 Accuracy"]),
        }
        for name, m in cv_scores.items()
    }).T.sort_values("Macro F1 (mean)", ascending=False)

    print(cv_summary.to_string())
    cv_summary.to_csv(config.CV_SUMMARY_PATH)

    if make_plots:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 5))
        means = cv_summary["Accuracy (mean)"]
        stds = cv_summary["Accuracy (std)"]
        ax.bar(means.index, means.values, yerr=stds.values, capsize=5, color="#4C72B0")
        ax.set_ylim(min(0.95, means.min() - 0.02), 1.005)
        ax.set_ylabel("CV Accuracy")
        ax.set_title(f"{config.N_SPLITS}-Fold Cross-Validated Accuracy (mean ± std)")
        plt.tight_layout()
        plt.savefig(config.OUTPUTS_DIR / "cv_accuracy.png", dpi=150)
        plt.close(fig)

    # ---- 10. Train final models -------------------------------------------
    section("10. Train final models (for downstream diagnostics)")
    trained_models = {}
    t0 = time.time()
    for name, model in make_models(n_classes).items():
        model.fit(X_train, y_train, X_test, y_test)
        trained_models[name] = model
        print(f"{name} trained ({time.time() - t0:.1f}s elapsed)")

    # ---- 11. Noise-robustness stress test ------------------------------------
    section("11. Noise-robustness stress test")
    col_std = noise_mod.compute_col_std(X_train)
    noise_levels = config.NOISE_LEVELS_FOR_ROBUSTNESS_TEST

    robustness = {name: [] for name in trained_models}
    for noise_level in noise_levels:
        X_noisy = noise_mod.inject_noise(
            X_test, col_std, noise_level, enabled=True, random_state=config.RANDOM_STATE
        )
        for name, model in trained_models.items():
            pred = np.asarray(model.predict(X_noisy)).reshape(-1)
            robustness[name].append(accuracy_score(y_test, pred))

    robustness_df = pd.DataFrame(robustness, index=[f"{n:.0%}" for n in noise_levels])
    robustness_df.index.name = "Injected noise (relative to within-class std)"
    print(robustness_df.to_string())
    robustness_df.to_csv(config.ROBUSTNESS_SUMMARY_PATH)

    if make_plots:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 6))
        for name in trained_models:
            ax.plot(noise_levels, robustness[name], marker="o", label=name, linewidth=2)
        ax.set_xlabel("Injected noise level (relative to within-class std)")
        ax.set_ylabel("Accuracy")
        ax.set_title("Model Accuracy Degradation Under Simulated Measurement Noise")
        ax.legend()
        ax.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(config.OUTPUTS_DIR / "noise_robustness.png", dpi=150)
        plt.close(fig)

    # Pick the model with the best AVERAGE accuracy across noise levels > 0
    robustness_excl_zero = robustness_df.iloc[1:]
    best_model_name = robustness_excl_zero.mean().idxmax()
    best_model = trained_models[best_model_name]

    print("\nModel ranked by robustness to noise (average accuracy across noise levels 10%-100%):")
    print(robustness_excl_zero.mean().sort_values(ascending=False).to_string())
    print("\nSELECTED MODEL:", best_model_name)

    # ---- 12. Detailed classification report ----------------------------------
    section("12. Detailed classification report (best model, clean test data)")
    y_pred_best = np.asarray(best_model.predict(X_test)).reshape(-1)
    print(classification_report(y_test, y_pred_best, target_names=class_names, zero_division=0))

    # ---- 13. Confusion matrices ------------------------------------------------
    section("13. Confusion matrix - clean vs. moderately noisy test data")
    X_test_noisy_25 = noise_mod.inject_noise(
        X_test, col_std, 0.25, enabled=True, random_state=config.RANDOM_STATE
    )
    y_pred_noisy = np.asarray(best_model.predict(X_test_noisy_25)).reshape(-1)

    if make_plots:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import seaborn as sns

        fig, axes = plt.subplots(1, 2, figsize=(28, 12))
        cm_clean = confusion_matrix(y_test, y_pred_best)
        sns.heatmap(cm_clean, cmap="Blues", xticklabels=class_names, yticklabels=class_names,
                    cbar=False, ax=axes[0])
        axes[0].set_title(f"{best_model_name} — Clean Test Data")
        axes[0].set_xlabel("Predicted")
        axes[0].set_ylabel("Actual")
        axes[0].tick_params(axis="x", rotation=90)

        cm_noisy = confusion_matrix(y_test, y_pred_noisy)
        sns.heatmap(cm_noisy, cmap="Reds", xticklabels=class_names, yticklabels=class_names,
                    cbar=False, ax=axes[1])
        axes[1].set_title(f"{best_model_name} — Test Data + 25% Noise")
        axes[1].set_xlabel("Predicted")
        axes[1].set_ylabel("Actual")
        axes[1].tick_params(axis="x", rotation=90)

        plt.tight_layout()
        plt.savefig(config.OUTPUTS_DIR / "confusion_matrices.png", dpi=150)
        plt.close(fig)
        print(f"Saved confusion matrices to {config.OUTPUTS_DIR / 'confusion_matrices.png'}")

    # ---- 14. Feature importance ------------------------------------------------
    section("14. Feature importance")
    importances = best_model.feature_importances_
    if importances is not None:
        importance = pd.DataFrame({
            "Feature": X.columns, "Importance": importances,
        }).sort_values("Importance", ascending=False)
        print(importance.to_string(index=False))

        if make_plots:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import seaborn as sns

            plt.figure(figsize=(10, 8))
            sns.barplot(data=importance, x="Importance", y="Feature")
            plt.title(f"Feature Importance — {best_model_name}")
            plt.tight_layout()
            plt.savefig(config.OUTPUTS_DIR / "feature_importance.png", dpi=150)
            plt.close()
    else:
        print(f"{best_model_name} does not expose feature_importances_.")

    # ---- 15. Save all models ----------------------------------------------------
    section("15. Save all models")
    for name, model in trained_models.items():
        key = model.key
        model.save(config.MODEL_REGISTRY[key]["pkl"])
        print(f"Saved {name} -> {config.MODEL_REGISTRY[key]['pkl']}")

    import joblib
    joblib.dump(label_encoder, config.LABEL_ENCODER_PATH)
    joblib.dump(list(X.columns), config.FEATURES_PATH)
    joblib.dump(best_model_name, config.BEST_MODEL_NAME_PATH)

    print("\nSaved models:", list(trained_models.keys()))
    print("Selected as default (most noise-robust):", best_model_name)

    return {
        "cv_summary": cv_summary,
        "robustness_df": robustness_df,
        "best_model_name": best_model_name,
        "trained_models": trained_models,
        "label_encoder": label_encoder,
        "features": list(X.columns),
    }


def main():
    parser = argparse.ArgumentParser(description="Train and compare all EDS component prediction models.")
    parser.add_argument("--data", default=str(config.DEFAULT_DATA_FILE),
                         help="Path to training data (.csv or .xlsx).")
    parser.add_argument("--no-plots", action="store_true", help="Skip saving PNG plots.")
    args = parser.parse_args()

    run(data_path=args.data, make_plots=not args.no_plots)


if __name__ == "__main__":
    main()
