"""
training/evaluate_rules.py
===========================
Cross-validation and comparative evaluation script for the rule engine.

Implements a simple Decision Tree (pure stdlib) for comparison.
Evaluates rule engine on held-out test set.
Computes accuracy, per-class precision/recall/F1, confusion matrix,
rule coverage, average confidence.

Usage:
    python training/evaluate_rules.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rule_engine.engine import RuleEngine
from rule_engine.preprocessing import (
    FEATURE_COLUMNS,
    load_csv_data,
    extract_features,
    extract_target,
    stratified_split,
)


class SimpleDecisionStump:
    """
    A simple single-feature decision tree (depth=1) for comparison.
    Pure stdlib implementation.
    """

    def __init__(self):
        self.feature: str = ""
        self.threshold: float = 0.0
        self.left_class: str = ""
        self.right_class: str = ""

    def fit(self, X: List[Dict[str, float]], y: List[str]) -> None:
        """Find the best single-feature split."""
        best_gini = float("inf")
        classes = list(set(y))

        for feature in FEATURE_COLUMNS:
            values = sorted(set(row[feature] for row in X))
            if len(values) <= 1:
                continue

            # Try midpoints between sorted unique values
            for i in range(len(values) - 1):
                threshold = (values[i] + values[i + 1]) / 2.0

                left_labels = [y[j] for j in range(len(X)) if X[j][feature] <= threshold]
                right_labels = [y[j] for j in range(len(X)) if X[j][feature] > threshold]

                if not left_labels or not right_labels:
                    continue

                gini = (
                    len(left_labels) / len(y) * _gini_impurity(left_labels) +
                    len(right_labels) / len(y) * _gini_impurity(right_labels)
                )

                if gini < best_gini:
                    best_gini = gini
                    self.feature = feature
                    self.threshold = threshold
                    self.left_class = _majority_class(left_labels)
                    self.right_class = _majority_class(right_labels)

    def predict(self, x: Dict[str, float]) -> str:
        """Predict class for a single sample."""
        if x.get(self.feature, 0.0) <= self.threshold:
            return self.left_class
        return self.right_class


class MajorityClassBaseline:
    """Always predict the most common class."""

    def __init__(self):
        self.majority_class: str = ""

    def fit(self, X: List[Dict[str, float]], y: List[str]) -> None:
        self.majority_class = _majority_class(y)

    def predict(self, x: Dict[str, float]) -> str:
        return self.majority_class


def compute_metrics(
    y_true: List[str],
    y_pred: List[str],
) -> Dict[str, Any]:
    """
    Compute accuracy, per-class precision/recall/F1, and confusion info.
    """
    classes = sorted(set(y_true) | set(y_pred))
    n = len(y_true)

    # Overall accuracy
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = correct / n if n > 0 else 0.0

    # Per-class metrics
    per_class: Dict[str, Dict[str, float]] = {}
    for cls in classes:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p == cls)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != cls and p == cls)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p != cls)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        per_class[cls] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": sum(1 for t in y_true if t == cls),
        }

    # Macro averages
    macro_precision = sum(m["precision"] for m in per_class.values()) / len(per_class) if per_class else 0.0
    macro_recall = sum(m["recall"] for m in per_class.values()) / len(per_class) if per_class else 0.0
    macro_f1 = sum(m["f1"] for m in per_class.values()) / len(per_class) if per_class else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "macro_precision": round(macro_precision, 4),
        "macro_recall": round(macro_recall, 4),
        "macro_f1": round(macro_f1, 4),
        "per_class": per_class,
        "total_samples": n,
        "correct": correct,
    }


def evaluate_rule_engine(
    engine: RuleEngine,
    test_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluate the rule engine on test data.

    Returns metrics plus coverage and confidence statistics.
    """
    y_true = []
    y_pred = []
    confidences = []
    statuses: Dict[str, int] = defaultdict(int)

    for row in test_data:
        features = extract_features(row)
        actual = extract_target(row)
        result = engine.predict(features)

        y_true.append(actual)
        y_pred.append(result.prediction)
        confidences.append(result.confidence)
        statuses[result.status] += 1

    metrics = compute_metrics(y_true, y_pred)
    metrics["coverage"] = {
        "matched": statuses.get("matched", 0),
        "low_confidence": statuses.get("low_confidence", 0),
        "no_match": statuses.get("no_match", 0),
        "total": len(test_data),
    }
    metrics["avg_confidence"] = (
        sum(confidences) / len(confidences) if confidences else 0.0
    )

    return metrics


def evaluate_baselines(
    train_data: List[Dict[str, Any]],
    test_data: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Evaluate baseline models for comparison."""
    # Prepare data
    X_train = [extract_features(r) for r in train_data]
    y_train = [extract_target(r) for r in train_data]
    X_test = [extract_features(r) for r in test_data]
    y_test = [extract_target(r) for r in test_data]

    results = {}

    # Majority class baseline
    majority = MajorityClassBaseline()
    majority.fit(X_train, y_train)
    y_pred_majority = [majority.predict(x) for x in X_test]
    results["majority_class"] = compute_metrics(y_test, y_pred_majority)
    results["majority_class"]["model"] = "Majority Class Baseline"

    # Decision stump baseline
    stump = SimpleDecisionStump()
    stump.fit(X_train, y_train)
    y_pred_stump = [stump.predict(x) for x in X_test]
    results["decision_stump"] = compute_metrics(y_test, y_pred_stump)
    results["decision_stump"]["model"] = "Decision Stump (depth=1)"
    results["decision_stump"]["feature"] = stump.feature
    results["decision_stump"]["threshold"] = stump.threshold

    return results


def main():
    """Run evaluation and generate report."""
    project_root = Path(__file__).resolve().parent.parent
    data_path = project_root / "data" / "synthetic_eds_data.csv"
    output_dir = project_root / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("EDS Rule Engine - Evaluation Report")
    print("=" * 60)

    # Load data and split
    print(f"\nLoading data from {data_path}...")
    data = load_csv_data(data_path)
    train_data, val_data, test_data = stratified_split(data)
    print(f"  Train: {len(train_data)}, Val: {len(val_data)}, Test: {len(test_data)}")

    # Evaluate rule engine
    print("\nEvaluating rule engine...")
    try:
        engine = RuleEngine()
        rule_metrics = evaluate_rule_engine(engine, test_data)
        print(f"  Rule Engine Accuracy: {rule_metrics['accuracy']:.2%}")
        print(f"  Macro F1: {rule_metrics['macro_f1']:.2%}")
        print(f"  Coverage: {rule_metrics['coverage']}")
        print(f"  Avg Confidence: {rule_metrics['avg_confidence']:.2%}")
    except FileNotFoundError:
        print("  WARNING: rules.json not found. Run train_rules.py first.")
        rule_metrics = {"error": "rules.json not found"}

    # Evaluate baselines
    print("\nEvaluating baselines...")
    baseline_metrics = evaluate_baselines(train_data, test_data)
    for name, metrics in baseline_metrics.items():
        print(f"  {metrics['model']}: accuracy={metrics['accuracy']:.2%}")

    # Build comprehensive report
    report = {
        "rule_engine": rule_metrics,
        "baselines": baseline_metrics,
        "data_split": {
            "train": len(train_data),
            "val": len(val_data),
            "test": len(test_data),
        },
    }

    # Save report
    report_path = output_dir / "evaluation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved to: {report_path}")

    # Print comparison table
    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)
    print(f"{'Model':<30} {'Accuracy':<12} {'Macro F1':<12}")
    print("-" * 54)
    if "accuracy" in rule_metrics:
        print(f"{'Rule Engine':<30} {rule_metrics['accuracy']:.4f}       {rule_metrics['macro_f1']:.4f}")
    for name, metrics in baseline_metrics.items():
        print(f"{metrics['model']:<30} {metrics['accuracy']:.4f}       {metrics['macro_f1']:.4f}")


def _gini_impurity(labels: List[str]) -> float:
    """Compute Gini impurity for a list of labels."""
    n = len(labels)
    if n == 0:
        return 0.0
    counts: Dict[str, int] = {}
    for label in labels:
        counts[label] = counts.get(label, 0) + 1
    return 1.0 - sum((c / n) ** 2 for c in counts.values())


def _majority_class(labels: List[str]) -> str:
    """Return the most common label."""
    counts: Dict[str, int] = {}
    for label in labels:
        counts[label] = counts.get(label, 0) + 1
    return max(counts, key=counts.get) if counts else ""


if __name__ == "__main__":
    main()
