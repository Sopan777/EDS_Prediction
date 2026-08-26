"""
rule_engine/validator.py
========================
Rule validation utilities for quality assurance.
Checks for contradictory rules, redundant rules, low-support rules,
and computes rule coverage statistics.

Pure Python stdlib - no external dependencies.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from rule_engine.models import Rule, RuleSet
from rule_engine.preprocessing import FEATURE_COLUMNS


def validate_ruleset(ruleset: RuleSet) -> Dict[str, Any]:
    """
    Perform comprehensive validation on a rule set.

    Returns a validation report dict with:
        - is_valid: bool
        - issues: list of issue descriptions
        - stats: coverage and quality statistics
    """
    issues: List[str] = []
    warnings: List[str] = []

    # Check basic structure
    if not ruleset.rules:
        issues.append("Rule set is empty - no rules defined")

    # Check for rules covering all expected features
    all_features_used = set()
    for rule in ruleset.rules:
        for cond in rule.conditions:
            all_features_used.add(cond.feature)

    unused_features = set(FEATURE_COLUMNS) - all_features_used
    if unused_features:
        warnings.append(f"Features not used in any rule: {sorted(unused_features)}")

    # Check for contradictory rules (same conditions, different predictions)
    contradictions = find_contradictory_rules(ruleset.rules)
    if contradictions:
        for pair in contradictions:
            issues.append(
                f"Contradictory rules: {pair[0].id} (predicts {pair[0].prediction}) "
                f"vs {pair[1].id} (predicts {pair[1].prediction})"
            )

    # Check for redundant rules
    redundant = find_redundant_rules(ruleset.rules)
    if redundant:
        for pair in redundant:
            warnings.append(f"Potentially redundant: {pair[0].id} and {pair[1].id}")

    # Check for low-support rules
    low_support = find_low_support_rules(ruleset.rules, min_support=3)
    if low_support:
        for rule in low_support:
            warnings.append(f"Low support rule: {rule.id} (support={rule.support})")

    # Coverage stats
    classes_covered = set(r.prediction for r in ruleset.rules)
    rules_per_class: Dict[str, int] = {}
    for rule in ruleset.rules:
        rules_per_class[rule.prediction] = rules_per_class.get(rule.prediction, 0) + 1

    stats = {
        "total_rules": len(ruleset.rules),
        "classes_covered": len(classes_covered),
        "features_used": len(all_features_used),
        "avg_conditions_per_rule": (
            sum(len(r.conditions) for r in ruleset.rules) / len(ruleset.rules)
            if ruleset.rules else 0
        ),
        "avg_confidence": (
            sum(r.confidence for r in ruleset.rules) / len(ruleset.rules)
            if ruleset.rules else 0
        ),
        "avg_validation_accuracy": (
            sum(r.validation_accuracy for r in ruleset.rules) / len(ruleset.rules)
            if ruleset.rules else 0
        ),
        "rules_per_class": rules_per_class,
    }

    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "stats": stats,
    }


def find_contradictory_rules(rules: List[Rule]) -> List[Tuple[Rule, Rule]]:
    """
    Find pairs of rules with identical conditions but different predictions.
    """
    contradictions: List[Tuple[Rule, Rule]] = []

    for i in range(len(rules)):
        for j in range(i + 1, len(rules)):
            if rules[i].prediction == rules[j].prediction:
                continue
            if _conditions_equivalent(rules[i], rules[j]):
                contradictions.append((rules[i], rules[j]))

    return contradictions


def find_redundant_rules(rules: List[Rule]) -> List[Tuple[Rule, Rule]]:
    """
    Find pairs of rules where one is a strict subset of another
    (same prediction, one's conditions are a subset of the other's).
    """
    redundant: List[Tuple[Rule, Rule]] = []

    for i in range(len(rules)):
        for j in range(i + 1, len(rules)):
            if rules[i].prediction != rules[j].prediction:
                continue
            if _is_subset_rule(rules[i], rules[j]):
                redundant.append((rules[i], rules[j]))
            elif _is_subset_rule(rules[j], rules[i]):
                redundant.append((rules[j], rules[i]))

    return redundant


def find_low_support_rules(rules: List[Rule], min_support: int = 3) -> List[Rule]:
    """Find rules with support below the minimum threshold."""
    return [r for r in rules if r.support < min_support]


def compute_coverage(
    rules: List[Rule],
    data: List[Dict[str, float]],
    labels: List[str],
) -> Dict[str, Any]:
    """
    Compute how well the rules cover a dataset.

    Returns coverage statistics including:
        - overall coverage (fraction of samples matched by at least one rule)
        - per-class coverage
        - average rules per sample
    """
    total = len(data)
    if total == 0:
        return {"overall_coverage": 0.0, "per_class": {}, "avg_rules_per_sample": 0.0}

    covered = 0
    correct = 0
    rules_per_sample: List[int] = []
    class_covered: Dict[str, int] = {}
    class_total: Dict[str, int] = {}

    for features, label in zip(data, labels):
        class_total[label] = class_total.get(label, 0) + 1

        matching_rules = [r for r in rules if r.evaluate(features)]
        rules_per_sample.append(len(matching_rules))

        if matching_rules:
            covered += 1
            class_covered[label] = class_covered.get(label, 0) + 1

            # Check if best matching rule gives correct prediction
            best = sorted(
                matching_rules,
                key=lambda r: (-r.validation_accuracy, -r.confidence, -r.support),
            )[0]
            if best.prediction == label:
                correct += 1

    per_class: Dict[str, Any] = {}
    for cls in sorted(class_total.keys()):
        per_class[cls] = {
            "coverage": class_covered.get(cls, 0) / class_total[cls] if class_total[cls] > 0 else 0.0,
            "total": class_total[cls],
            "covered": class_covered.get(cls, 0),
        }

    return {
        "overall_coverage": covered / total if total > 0 else 0.0,
        "overall_accuracy": correct / total if total > 0 else 0.0,
        "per_class": per_class,
        "avg_rules_per_sample": sum(rules_per_sample) / total if total > 0 else 0.0,
        "samples_with_no_match": total - covered,
    }


def _conditions_equivalent(rule1: Rule, rule2: Rule) -> bool:
    """Check if two rules have equivalent conditions (same feature/op/threshold sets)."""
    if len(rule1.conditions) != len(rule2.conditions):
        return False

    conds1 = sorted(
        [(c.feature, c.operator, c.threshold) for c in rule1.conditions]
    )
    conds2 = sorted(
        [(c.feature, c.operator, c.threshold) for c in rule2.conditions]
    )
    return conds1 == conds2


def _is_subset_rule(sub: Rule, parent: Rule) -> bool:
    """Check if sub's conditions are a strict subset of parent's conditions."""
    if len(sub.conditions) >= len(parent.conditions):
        return False

    sub_conds = set(
        (c.feature, c.operator, c.threshold) for c in sub.conditions
    )
    parent_conds = set(
        (c.feature, c.operator, c.threshold) for c in parent.conditions
    )
    return sub_conds.issubset(parent_conds)


# ---------------------------------------------------------------------------
# Schema validation for the NEW knowledge base (rule_engine/knowledge/
# materials.json), consumed by rule_engine.scoring.KnowledgeBase.
#
# The functions above (validate_ruleset, find_contradictory_rules, etc.)
# operate on the retired Rule/RuleSet format from rule_engine/rules/rules.json
# and are kept only for the quarantined legacy suite (tests/test_validator.py,
# run with --run-legacy). They do not apply to materials.json's structure and
# were never called at runtime for either format - this is what fixes that:
# KnowledgeBase.load() calls validate_knowledge_base() and refuses to start on
# a structurally broken file instead of failing confusingly deep inside
# scoring.
# ---------------------------------------------------------------------------


def validate_knowledge_base(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the structure of a loaded materials.json dict.

    Checks the shape scoring.score_family actually relies on: every family has
    a label and an elements dict, every element band is a well-formed
    [lo, hi] pair with lo <= hi, and every discriminator names either an
    element present in that family's own elements dict or a ratio with a
    matching entry in that family's ratios list. A discriminator naming
    neither would silently score as 0 evidence for that term - wrong, and
    quiet about it - rather than raising where the mistake was made.

    Returns ``{"is_valid": bool, "issues": [...], "warnings": [...]}``.
    ``issues`` are structural problems severe enough that the caller should
    refuse to run; ``warnings`` are worth surfacing but not fatal.
    """
    issues: List[str] = []
    warnings: List[str] = []

    families = data.get("families")
    if not isinstance(families, dict) or not families:
        issues.append("no 'families' dict, or it is empty")
        return {"is_valid": False, "issues": issues, "warnings": warnings}

    all_components: set = set()
    for fid, fam in families.items():
        if not isinstance(fam, dict):
            issues.append(fid + ": family entry is not a dict")
            continue
        if not fam.get("label"):
            issues.append(fid + ": missing 'label'")

        elements = fam.get("elements")
        if not isinstance(elements, dict):
            issues.append(fid + ": missing or malformed 'elements' dict")
            elements = {}

        for element, spec in elements.items():
            band = spec.get("band_wt") if isinstance(spec, dict) else None
            if not isinstance(band, list) or len(band) != 2:
                issues.append(fid + "." + element + ": band_wt is not a [lo, hi] pair")
                continue
            lo, hi = band
            if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
                issues.append(fid + "." + element + ": band_wt values are not numeric")
            elif lo > hi:
                issues.append(
                    fid + "." + element + ": band_wt lo > hi (" + str(band) + ")"
                )

        ratio_names = {
            r.get("ratio")
            for r in fam.get("ratios", [])
            if isinstance(r, dict)
        }
        for ratio in fam.get("ratios", []):
            if not isinstance(ratio, dict):
                issues.append(fid + ": a ratio entry is not a dict")
                continue
            lo, hi = ratio.get("min"), ratio.get("max")
            if isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and lo > hi:
                issues.append(
                    fid + "." + str(ratio.get("ratio")) + ": ratio min > max"
                )

        for disc in fam.get("discriminators", []):
            if "/" in disc:
                if disc not in ratio_names:
                    issues.append(
                        fid
                        + ": discriminator "
                        + repr(disc)
                        + " names a ratio with no matching entry in this "
                        + "family's ratios list"
                    )
            elif disc not in elements:
                issues.append(
                    fid
                    + ": discriminator "
                    + repr(disc)
                    + " is not in this family's own elements dict"
                )

        components = fam.get("components", [])
        if not components:
            warnings.append(fid + ": no candidate components listed")
        all_components.update(components)

    if not all_components:
        warnings.append("no family lists any candidate components")

    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
    }
