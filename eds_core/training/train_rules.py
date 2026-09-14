"""
training/train_rules.py
========================
Main rule generation script for the EDS rule-based prediction engine.

Algorithm:
    1. Load CSV using stdlib csv module
    2. Split data into train/validation/test (80/10/10) with stratification
    3. For each class, compute per-feature min/max ranges from training data
    4. Generate candidate rules based on range conditions
    5. Validate each rule on validation set (precision/recall/support)
    6. Prune redundant conditions that don't improve precision
    7. Assign priorities based on validation precision and specificity
    8. Compute dataset hash for versioning
    9. Output versioned rules.json

Usage:
    python training/train_rules.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rule_engine.models import Condition, Rule, RuleSet
from rule_engine.preprocessing import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    load_csv_data,
    extract_features,
    extract_target,
    stratified_split,
    compute_feature_stats,
)


def compute_dataset_hash(file_path: Path) -> str:
    """Compute SHA256 hash of the dataset file for versioning."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()[:16]


def generate_rules_for_class(
    class_name: str,
    train_data: List[Dict[str, Any]],
    all_train_data: List[Dict[str, Any]],
    tolerance_factor: float = 0.10,
) -> List[Rule]:
    """
    Generate candidate rules for a single class based on feature ranges.

    For each feature, if the class has a distinctive range (non-zero values
    that are separable from other classes), create range conditions.

    Args:
        class_name: The target class name
        train_data: Training data for this class only
        all_train_data: All training data (for computing other-class ranges)
        tolerance_factor: Fraction of range to add as tolerance margin

    Returns:
        List of candidate Rule objects for this class
    """
    # Get feature stats for this class
    class_stats = compute_feature_stats(
        [r for r in all_train_data if extract_target(r) == class_name],
        class_name,
    )

    # Get per-other-class stats for more nuanced separation
    other_classes = sorted(set(extract_target(r) for r in all_train_data) - {class_name})
    other_class_stats: Dict[str, Dict[str, Dict[str, float]]] = {}
    for other_cls in other_classes:
        other_class_stats[other_cls] = compute_feature_stats(
            [r for r in all_train_data if extract_target(r) == other_cls],
            other_cls,
        )

    # Get combined other-class stats
    other_data = [r for r in all_train_data if extract_target(r) != class_name]
    other_stats: Dict[str, Dict[str, float]] = {}
    for col in FEATURE_COLUMNS:
        values = [float(r.get(col, 0.0)) for r in other_data]
        if values:
            other_stats[col] = {
                "min": min(values),
                "max": max(values),
                "mean": sum(values) / len(values),
                "nonzero_count": sum(1 for v in values if v != 0.0),
            }
        else:
            other_stats[col] = {"min": 0.0, "max": 0.0, "mean": 0.0, "nonzero_count": 0}

    # Identify discriminating conditions for this class
    # Each condition has a discrimination score
    condition_candidates: List[Tuple[Condition, float]] = []

    for col in FEATURE_COLUMNS:
        cs = class_stats[col]
        os = other_stats[col]

        # Skip features with no non-zero values for this class
        if cs["nonzero_count"] == 0 and cs["max"] == 0.0:
            # Feature is always zero for this class
            # If many other classes also have zero, this is not very discriminating
            # But if most other classes have non-zero, a <= 0 condition helps
            if os["nonzero_count"] > len(other_data) * 0.5:
                condition_candidates.append(
                    (Condition(feature=col, operator="<=", threshold=0.0), 0.4)
                )
            continue

        # Compute tolerance margin
        class_range = cs["max"] - cs["min"]
        tolerance = class_range * tolerance_factor if class_range > 0 else 0.05

        # Case 1: Feature is uniquely non-zero for this class
        # (other classes are all zero)
        if os["max"] == 0.0 and cs["nonzero_count"] > 0:
            # Strong discriminator - feature only present in this class
            lower_bound = max(0.0, cs["min"] - tolerance)
            condition_candidates.append(
                (Condition(feature=col, operator=">=", threshold=round(lower_bound, 2)), 1.0)
            )
            continue

        # Case 2: Feature has a distinct lower bound well above others
        if cs["min"] > os["max"] and cs["min"] > 0:
            lower_bound = max(0.0, cs["min"] - tolerance)
            condition_candidates.append(
                (Condition(feature=col, operator=">=", threshold=round(lower_bound, 2)), 0.95)
            )
            continue

        # Case 3: Feature has a distinct upper bound well below others' min
        if cs["max"] < os["min"] and os["min"] > 0:
            upper_bound = cs["max"] + tolerance
            condition_candidates.append(
                (Condition(feature=col, operator="<=", threshold=round(upper_bound, 2)), 0.95)
            )
            continue

        # Case 4: Feature range is non-overlapping with most other classes
        if cs["nonzero_count"] > 0:
            overlap_start = max(cs["min"], os["min"]) if os["nonzero_count"] > 0 else cs["min"]
            overlap_end = min(cs["max"], os["max"]) if os["nonzero_count"] > 0 else cs["max"]

            if overlap_start > overlap_end:
                # No overlap - ranges are fully separable
                lower_bound = max(0.0, cs["min"] - tolerance)
                upper_bound = cs["max"] + tolerance
                condition_candidates.append(
                    (Condition(feature=col, operator=">=", threshold=round(lower_bound, 2)), 0.85)
                )
                condition_candidates.append(
                    (Condition(feature=col, operator="<=", threshold=round(upper_bound, 2)), 0.85)
                )
            elif cs["mean"] > 0 and cs["nonzero_count"] == cs["total_count"]:
                # Feature always present for this class - use range
                lower_bound = max(0.0, cs["min"] - tolerance)
                upper_bound = cs["max"] + tolerance

                # Compute how discriminating this range is
                # Count how many other-class samples fall in this range
                others_in_range = sum(
                    1 for r in other_data
                    if lower_bound <= float(r.get(col, 0.0)) <= upper_bound
                )
                discrimination = 1.0 - (others_in_range / len(other_data)) if other_data else 0.0

                if discrimination > 0.5:
                    condition_candidates.append(
                        (Condition(feature=col, operator=">=", threshold=round(lower_bound, 2)), discrimination * 0.8)
                    )
                    condition_candidates.append(
                        (Condition(feature=col, operator="<=", threshold=round(upper_bound, 2)), discrimination * 0.8)
                    )

    if not condition_candidates:
        return []

    # Sort by discrimination score and take the best conditions
    condition_candidates.sort(key=lambda x: -x[1])

    # Take all conditions with score > 0.3
    conditions = [c for c, score in condition_candidates if score > 0.3]

    if not conditions:
        # If no strong conditions, take the top 3
        conditions = [c for c, _ in condition_candidates[:3]]

    # Build a single comprehensive rule with all discriminating conditions
    n_class_samples = len(train_data)
    rule_id = f"rule_{_sanitize_name(class_name)}_primary"

    rule = Rule(
        id=rule_id,
        conditions=conditions,
        prediction=class_name,
        confidence=0.0,  # Will be set during validation
        support=n_class_samples,
        validation_accuracy=0.0,  # Will be set during validation
        priority=0,  # Will be set after validation
        description=f"Range-based rule for {class_name} ({len(conditions)} conditions)",
    )

    return [rule]


def validate_rules(
    rules: List[Rule],
    val_data: List[Dict[str, Any]],
    min_precision: float = 0.3,
) -> List[Rule]:
    """
    Validate rules on validation set, computing precision, recall, and accuracy.

    Updates each rule's confidence and validation_accuracy in place.
    Returns rules sorted by validation performance.
    """
    validated_rules: List[Rule] = []

    for rule in rules:
        # Count true positives, false positives, and false negatives
        tp = 0
        fp = 0
        fn = 0
        total_class = 0

        for row in val_data:
            features = extract_features(row)
            actual = extract_target(row)
            matches = rule.evaluate(features)

            if actual == rule.prediction:
                total_class += 1
                if matches:
                    tp += 1
                else:
                    fn += 1
            else:
                if matches:
                    fp += 1

        # Compute metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / total_class if total_class > 0 else 0.0

        # Update rule with validation metrics
        rule.confidence = round(precision, 4)
        rule.validation_accuracy = round(precision, 4)

        # Only keep rules with reasonable precision
        if precision >= min_precision or (tp > 0 and fp == 0):
            validated_rules.append(rule)

    return validated_rules


def prune_rules(rules: List[Rule], train_data: List[Dict[str, Any]]) -> List[Rule]:
    """
    Prune redundant conditions from rules.

    For each rule, try removing conditions one at a time and check if
    precision is maintained or improved on training data.
    """
    pruned_rules: List[Rule] = []

    for rule in rules:
        if len(rule.conditions) <= 1:
            pruned_rules.append(rule)
            continue

        # Try removing each condition and measure impact
        best_conditions = rule.conditions[:]
        improved = True

        while improved and len(best_conditions) > 1:
            improved = False
            for i in range(len(best_conditions)):
                # Try removing condition i
                test_conditions = best_conditions[:i] + best_conditions[i + 1:]
                test_rule = Rule(
                    id=rule.id,
                    conditions=test_conditions,
                    prediction=rule.prediction,
                    confidence=rule.confidence,
                    support=rule.support,
                    validation_accuracy=rule.validation_accuracy,
                    priority=rule.priority,
                    description=rule.description,
                )

                # Evaluate on training data
                tp_new = 0
                fp_new = 0
                for row in train_data:
                    features = extract_features(row)
                    actual = extract_target(row)
                    if test_rule.evaluate(features):
                        if actual == rule.prediction:
                            tp_new += 1
                        else:
                            fp_new += 1

                new_precision = tp_new / (tp_new + fp_new) if (tp_new + fp_new) > 0 else 0.0

                # Keep the simpler rule if precision is still high
                if new_precision >= rule.confidence * 0.95 and tp_new > 0:
                    best_conditions = test_conditions
                    improved = True
                    break

        rule.conditions = best_conditions
        rule.description = f"Range-based rule for {rule.prediction} ({len(best_conditions)} conditions)"
        pruned_rules.append(rule)

    return pruned_rules


def assign_priorities(rules: List[Rule]) -> List[Rule]:
    """
    Assign priority scores to rules based on validation accuracy and specificity.

    Higher priority = better rule. Scale: 0-1000.
    """
    for rule in rules:
        # Priority based on:
        # - Validation accuracy (0-500 points)
        # - Specificity / num conditions (0-200 points)
        # - Support (0-300 points)
        acc_score = int(rule.validation_accuracy * 500)
        spec_score = min(200, len(rule.conditions) * 30)
        support_score = min(300, rule.support * 3)

        rule.priority = acc_score + spec_score + support_score

    return rules


def generate_fallback_rules(
    train_data: List[Dict[str, Any]],
    existing_rules: List[Rule],
) -> List[Rule]:
    """
    Generate simpler fallback rules for classes not well covered by primary rules.

    Uses the most discriminating single feature for each class.
    Generates rules for classes that either have no rules or have rules with
    low confidence.
    """
    covered_classes = set(r.prediction for r in existing_rules if r.confidence >= 0.3)
    all_classes = set(extract_target(r) for r in train_data)
    uncovered = all_classes - covered_classes

    fallback_rules: List[Rule] = []

    for cls in sorted(uncovered):
        class_data = [r for r in train_data if extract_target(r) == cls]
        other_data = [r for r in train_data if extract_target(r) != cls]

        if not class_data:
            continue

        # Find the single best discriminating feature
        best_feature = None
        best_score = -1.0
        best_conditions: List[Condition] = []

        for col in FEATURE_COLUMNS:
            class_values = [float(r.get(col, 0.0)) for r in class_data]
            other_values = [float(r.get(col, 0.0)) for r in other_data]

            class_nonzero = [v for v in class_values if v > 0]
            other_nonzero = [v for v in other_values if v > 0]

            if not class_nonzero:
                continue

            class_min = min(class_values)
            class_max = max(class_values)
            other_max = max(other_values) if other_values else 0.0

            # Score: how well this feature separates the class
            # Perfect if class range doesn't overlap with others
            if class_min > other_max:
                score = 1.0
            elif class_nonzero and not other_nonzero:
                score = 0.95
            else:
                # Partial overlap
                overlap = max(0, min(class_max, other_max) - max(class_min, min(other_values) if other_values else 0))
                total_range = class_max - class_min if class_max > class_min else 1.0
                score = max(0, 1.0 - overlap / total_range)

            if score > best_score:
                best_score = score
                best_feature = col
                tolerance = (class_max - class_min) * 0.2 if class_max > class_min else 0.1
                best_conditions = [
                    Condition(feature=col, operator=">=", threshold=round(max(0, class_min - tolerance), 2)),
                    Condition(feature=col, operator="<=", threshold=round(class_max + tolerance, 2)),
                ]

        if best_conditions and best_feature:
            rule = Rule(
                id=f"rule_{_sanitize_name(cls)}_fallback",
                conditions=best_conditions,
                prediction=cls,
                confidence=0.0,
                support=len(class_data),
                validation_accuracy=0.0,
                priority=0,
                description=f"Fallback rule for {cls} using {best_feature}",
            )
            fallback_rules.append(rule)

    return fallback_rules


def train_rules(data_path: Path, output_dir: Path) -> RuleSet:
    """
    Main training pipeline for rule generation.

    Args:
        data_path: Path to the training CSV file
        output_dir: Directory to write rules.json and evaluation report

    Returns:
        Generated RuleSet
    """
    print(f"Loading data from {data_path}...")
    data = load_csv_data(data_path)
    print(f"  Loaded {len(data)} rows")

    # Split data
    print("Splitting data (80/10/10 stratified)...")
    train_data, val_data, test_data = stratified_split(data)
    print(f"  Train: {len(train_data)}, Validation: {len(val_data)}, Test: {len(test_data)}")

    # Get all classes
    all_classes = sorted(set(extract_target(r) for r in train_data))
    print(f"  Classes: {len(all_classes)}")

    # Generate rules for each class
    print("\nGenerating rules...")
    all_rules: List[Rule] = []
    for cls in all_classes:
        class_train = [r for r in train_data if extract_target(r) == cls]
        rules = generate_rules_for_class(cls, class_train, train_data)
        all_rules.extend(rules)
        if rules:
            print(f"  {cls}: {len(rules)} rule(s), {len(rules[0].conditions)} conditions")
        else:
            print(f"  {cls}: no primary rules generated")

    print(f"\n  Total candidate rules: {len(all_rules)}")

    # Validate rules
    print("\nValidating rules on validation set...")
    validated_rules = validate_rules(all_rules, val_data)
    print(f"  Rules passing validation: {len(validated_rules)}")

    # Generate fallback rules for uncovered classes
    print("\nGenerating fallback rules for uncovered classes...")
    fallback_rules = generate_fallback_rules(train_data, validated_rules)
    if fallback_rules:
        # Validate fallback rules with lower threshold
        validated_fallbacks = validate_rules(fallback_rules, val_data, min_precision=0.0)
        validated_rules.extend(validated_fallbacks)
        print(f"  Added {len(validated_fallbacks)} fallback rules")

    # Prune redundant conditions
    print("\nPruning redundant conditions...")
    pruned_rules = prune_rules(validated_rules, train_data)
    print(f"  Rules after pruning: {len(pruned_rules)}")

    # Assign priorities
    print("\nAssigning priorities...")
    final_rules = assign_priorities(pruned_rules)

    # Sort by priority (highest first)
    final_rules.sort(key=lambda r: (-r.priority, r.id))

    # Evaluate on test set
    print("\nEvaluating on test set...")
    eval_result = evaluate_on_dataset(final_rules, test_data)
    test_accuracy = eval_result["accuracy"]
    print(f"  Test accuracy: {test_accuracy:.2%}")
    print(f"  Correct: {eval_result['correct']}/{eval_result['total']}")
    print(f"  Wrong predictions: {eval_result['wrong_predictions']}")
    print(f"  No match (no rule fired): {eval_result['no_match_count']}")

    # Compute dataset hash
    dataset_hash = compute_dataset_hash(data_path)

    # Build RuleSet
    ruleset = RuleSet(
        version="1.0.0",
        generated_at=datetime.now(timezone.utc).isoformat(),
        dataset_hash=dataset_hash,
        algorithm="range_based_with_pruning",
        validation_score=test_accuracy,
        rules_count=len(final_rules),
        rules=final_rules,
        metadata={
            "feature_columns": FEATURE_COLUMNS,
            "n_classes": len(all_classes),
            "classes": all_classes,
            "train_size": len(train_data),
            "val_size": len(val_data),
            "test_size": len(test_data),
            "test_accuracy": test_accuracy,
            "tolerance_factor": 0.15,
            "random_seed": 42,
        },
    )

    return ruleset


def evaluate_on_dataset(rules: List[Rule], data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluate rules on a dataset, returning accuracy and breakdown metrics.

    Returns a dict with:
        - accuracy: float (correct / total)
        - correct: int
        - wrong_predictions: int (rule fired but predicted wrong class)
        - no_match_count: int (no rule matched at all)
        - total: int
    """
    if not data:
        return {"accuracy": 0.0, "correct": 0, "wrong_predictions": 0, "no_match_count": 0, "total": 0}

    correct = 0
    wrong_predictions = 0
    no_match_count = 0
    total = len(data)

    for row in data:
        features = extract_features(row)
        actual = extract_target(row)

        # Find matching rules
        matches = [(r, r.evaluate(features)) for r in rules]
        matching_rules = [r for r, m in matches if m]

        if matching_rules:
            # Use conflict resolution: best by validation_accuracy, then confidence, then support
            best = sorted(
                matching_rules,
                key=lambda r: (-r.validation_accuracy, -r.confidence, -r.support, -r.specificity, r.id),
            )[0]
            if best.prediction == actual:
                correct += 1
            else:
                wrong_predictions += 1
        else:
            no_match_count += 1

    accuracy = correct / total if total > 0 else 0.0
    return {
        "accuracy": accuracy,
        "correct": correct,
        "wrong_predictions": wrong_predictions,
        "no_match_count": no_match_count,
        "total": total,
    }


def _sanitize_name(name: str) -> str:
    """Convert a class name to a safe identifier."""
    return name.lower().replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "")


def main():
    """Run the rule generation pipeline."""
    project_root = Path(__file__).resolve().parent.parent
    data_path = project_root / "data" / "synthetic_eds_data.csv"
    rules_dir = project_root / "rule_engine" / "rules"
    output_dir = project_root / "outputs"

    rules_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("EDS Rule-Based Prediction Engine - Rule Generation")
    print("=" * 60)

    # Generate rules
    ruleset = train_rules(data_path, output_dir)

    # Save rules
    rules_path = rules_dir / "rules.json"
    with open(rules_path, "w", encoding="utf-8") as f:
        json.dump(ruleset.to_dict(), f, indent=2)
    print(f"\nRules saved to: {rules_path}")

    # Save evaluation report
    report = {
        "version": ruleset.version,
        "generated_at": ruleset.generated_at,
        "dataset_hash": ruleset.dataset_hash,
        "algorithm": ruleset.algorithm,
        "validation_score": ruleset.validation_score,
        "rules_count": ruleset.rules_count,
        "metadata": ruleset.metadata,
        "rules_summary": [
            {
                "id": r.id,
                "prediction": r.prediction,
                "conditions_count": len(r.conditions),
                "confidence": r.confidence,
                "validation_accuracy": r.validation_accuracy,
                "priority": r.priority,
            }
            for r in ruleset.rules
        ],
    }
    report_path = output_dir / "rule_generation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved to: {report_path}")

    print(f"\nSummary:")
    print(f"  Total rules: {ruleset.rules_count}")
    print(f"  Classes covered: {ruleset.metadata['n_classes']}")
    print(f"  Test accuracy: {ruleset.validation_score:.2%}")
    print(f"  Algorithm: {ruleset.algorithm}")


if __name__ == "__main__":
    main()
