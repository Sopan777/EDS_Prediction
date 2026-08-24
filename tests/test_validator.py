"""
tests/test_validator.py
=======================
Tests for the rule validation utilities.
Tests validate_ruleset, find_contradictory_rules, find_redundant_rules,
find_low_support_rules, and compute_coverage.
Uses only pytest + stdlib (no pandas/numpy).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from rule_engine.models import Condition, Rule, RuleSet
from rule_engine.validator import (
    validate_ruleset,
    find_contradictory_rules,
    find_redundant_rules,
    find_low_support_rules,
    compute_coverage,
)
from rule_engine.preprocessing import FEATURE_COLUMNS, load_csv_data, extract_features, extract_target


RULES_PATH = Path(__file__).resolve().parent.parent / "rule_engine" / "rules" / "rules.json"
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "synthetic_eds_data.csv"


class TestValidateRuleset:
    """Test validate_ruleset on the actual rules.json."""

    def test_actual_ruleset_is_valid(self):
        """The production rules.json should pass validation."""
        with open(RULES_PATH) as f:
            data = json.load(f)
        ruleset = RuleSet.from_dict(data)
        report = validate_ruleset(ruleset)
        assert report["is_valid"] is True
        assert len(report["issues"]) == 0

    def test_validation_report_structure(self):
        """Validation report should have expected keys."""
        with open(RULES_PATH) as f:
            data = json.load(f)
        ruleset = RuleSet.from_dict(data)
        report = validate_ruleset(ruleset)
        assert "is_valid" in report
        assert "issues" in report
        assert "warnings" in report
        assert "stats" in report

    def test_validation_stats_structure(self):
        """Stats section should have expected metrics."""
        with open(RULES_PATH) as f:
            data = json.load(f)
        ruleset = RuleSet.from_dict(data)
        report = validate_ruleset(ruleset)
        stats = report["stats"]
        assert "total_rules" in stats
        assert "classes_covered" in stats
        assert "features_used" in stats
        assert "avg_conditions_per_rule" in stats
        assert "avg_confidence" in stats
        assert "avg_validation_accuracy" in stats
        assert "rules_per_class" in stats
        assert stats["total_rules"] == 36
        assert stats["classes_covered"] == 36

    def test_empty_ruleset_is_invalid(self):
        """An empty rule set should fail validation."""
        ruleset = RuleSet(
            version="1.0.0",
            generated_at="2024-01-01",
            dataset_hash="test",
            algorithm="test",
            validation_score=0.0,
            rules_count=0,
            rules=[],
        )
        report = validate_ruleset(ruleset)
        assert report["is_valid"] is False
        assert any("empty" in issue.lower() for issue in report["issues"])


class TestFindContradictoryRules:
    """Test find_contradictory_rules with test cases."""

    def test_no_contradictions_in_production_rules(self):
        """Production rules should have no contradictions."""
        with open(RULES_PATH) as f:
            data = json.load(f)
        ruleset = RuleSet.from_dict(data)
        contradictions = find_contradictory_rules(ruleset.rules)
        assert len(contradictions) == 0

    def test_detect_contradictory_rules(self):
        """Two rules with same conditions but different predictions are contradictory."""
        rule1 = Rule(
            id="rule_a",
            conditions=[Condition("Cr", ">=", 5.0), Condition("Cr", "<=", 10.0)],
            prediction="ClassA",
        )
        rule2 = Rule(
            id="rule_b",
            conditions=[Condition("Cr", ">=", 5.0), Condition("Cr", "<=", 10.0)],
            prediction="ClassB",
        )
        contradictions = find_contradictory_rules([rule1, rule2])
        assert len(contradictions) == 1
        assert contradictions[0][0].id == "rule_a"
        assert contradictions[0][1].id == "rule_b"

    def test_no_contradiction_same_prediction(self):
        """Two rules with same conditions and same prediction are NOT contradictory."""
        rule1 = Rule(
            id="rule_a",
            conditions=[Condition("Cr", ">=", 5.0)],
            prediction="ClassA",
        )
        rule2 = Rule(
            id="rule_b",
            conditions=[Condition("Cr", ">=", 5.0)],
            prediction="ClassA",
        )
        contradictions = find_contradictory_rules([rule1, rule2])
        assert len(contradictions) == 0

    def test_different_conditions_not_contradictory(self):
        """Rules with different conditions are not contradictory."""
        rule1 = Rule(
            id="rule_a",
            conditions=[Condition("Cr", ">=", 5.0)],
            prediction="ClassA",
        )
        rule2 = Rule(
            id="rule_b",
            conditions=[Condition("Ni", ">=", 5.0)],
            prediction="ClassB",
        )
        contradictions = find_contradictory_rules([rule1, rule2])
        assert len(contradictions) == 0


class TestFindRedundantRules:
    """Test find_redundant_rules with test cases."""

    def test_no_redundancy_in_production_rules(self):
        """Production rules should have no redundant rules (1 per class)."""
        with open(RULES_PATH) as f:
            data = json.load(f)
        ruleset = RuleSet.from_dict(data)
        redundant = find_redundant_rules(ruleset.rules)
        # With one rule per class (all different predictions), there can be no redundancy
        assert len(redundant) == 0

    def test_detect_subset_redundancy(self):
        """A rule whose conditions are a subset of another (same prediction) is redundant."""
        rule_specific = Rule(
            id="rule_specific",
            conditions=[
                Condition("Cr", ">=", 5.0),
                Condition("Cr", "<=", 10.0),
                Condition("Ni", ">=", 2.0),
            ],
            prediction="ClassA",
        )
        rule_general = Rule(
            id="rule_general",
            conditions=[Condition("Cr", ">=", 5.0)],
            prediction="ClassA",
        )
        redundant = find_redundant_rules([rule_specific, rule_general])
        assert len(redundant) == 1

    def test_no_redundancy_different_predictions(self):
        """Rules with different predictions cannot be redundant."""
        rule1 = Rule(
            id="rule_a",
            conditions=[Condition("Cr", ">=", 5.0)],
            prediction="ClassA",
        )
        rule2 = Rule(
            id="rule_b",
            conditions=[Condition("Cr", ">=", 5.0), Condition("Ni", ">=", 2.0)],
            prediction="ClassB",
        )
        redundant = find_redundant_rules([rule1, rule2])
        assert len(redundant) == 0


class TestFindLowSupportRules:
    """Test find_low_support_rules."""

    def test_production_rules_have_sufficient_support(self):
        """All production rules should have support >= 3."""
        with open(RULES_PATH) as f:
            data = json.load(f)
        ruleset = RuleSet.from_dict(data)
        low_support = find_low_support_rules(ruleset.rules, min_support=3)
        assert len(low_support) == 0

    def test_detect_low_support_rules(self):
        """Rules with support below threshold should be detected."""
        rules = [
            Rule(id="r1", conditions=[Condition("Cr", ">=", 1.0)],
                 prediction="A", support=1),
            Rule(id="r2", conditions=[Condition("Ni", ">=", 2.0)],
                 prediction="B", support=50),
            Rule(id="r3", conditions=[Condition("Mo", ">=", 3.0)],
                 prediction="C", support=2),
        ]
        low = find_low_support_rules(rules, min_support=5)
        assert len(low) == 2
        assert any(r.id == "r1" for r in low)
        assert any(r.id == "r3" for r in low)

    def test_empty_rules_list(self):
        """Empty rules list should return empty."""
        assert find_low_support_rules([], min_support=5) == []


class TestComputeCoverage:
    """Test compute_coverage on sample data."""

    def test_coverage_on_sample_data(self):
        """Coverage computation on a subset of the training data."""
        with open(RULES_PATH) as f:
            data = json.load(f)
        ruleset = RuleSet.from_dict(data)

        csv_data = load_csv_data(DATA_PATH)
        # Use first 100 samples
        subset = csv_data[:100]
        features_list = [extract_features(row) for row in subset]
        labels_list = [extract_target(row).strip() for row in subset]

        coverage = compute_coverage(ruleset.rules, features_list, labels_list)
        assert "overall_coverage" in coverage
        assert "overall_accuracy" in coverage
        assert "per_class" in coverage
        assert "avg_rules_per_sample" in coverage
        assert 0.0 <= coverage["overall_coverage"] <= 1.0
        assert 0.0 <= coverage["overall_accuracy"] <= 1.0

    def test_coverage_empty_data(self):
        """Coverage with empty data returns zero coverage."""
        rules = [Rule(id="r1", conditions=[Condition("Cr", ">=", 5.0)],
                      prediction="A")]
        coverage = compute_coverage(rules, [], [])
        assert coverage["overall_coverage"] == 0.0
        assert coverage["avg_rules_per_sample"] == 0.0

    def test_coverage_no_rules(self):
        """Coverage with no rules returns zero coverage."""
        features = [{"Cr": 5.0, "Ni": 3.0}]
        labels = ["ClassA"]
        coverage = compute_coverage([], features, labels)
        assert coverage["overall_coverage"] == 0.0
        assert coverage["samples_with_no_match"] == 1

    def test_coverage_perfect_match(self):
        """Rules that match all data should give 100% coverage."""
        # A rule that matches everything (>= 0 for a feature)
        rules = [Rule(
            id="r_all",
            conditions=[Condition("Cr", ">=", 0.0)],
            prediction="ClassA",
            validation_accuracy=1.0,
            confidence=1.0,
            support=100,
        )]
        features = [{"Cr": 5.0}, {"Cr": 10.0}, {"Cr": 0.0}]
        labels = ["ClassA", "ClassA", "ClassA"]
        coverage = compute_coverage(rules, features, labels)
        assert coverage["overall_coverage"] == 1.0
        assert coverage["overall_accuracy"] == 1.0
