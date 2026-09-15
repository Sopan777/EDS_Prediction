"""
tests/test_rule_engine.py
=========================
Tests for the rule-based prediction engine.
Uses only pytest (no external dependencies).
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from rule_engine.models import Condition, Rule, RuleMatch, PredictionResult, RuleSet
from rule_engine.preprocessing import (
    FEATURE_COLUMNS,
    validate_input,
    load_csv_data,
    extract_features,
    extract_target,
    stratified_split,
)
from rule_engine.engine import RuleEngine
from rule_engine.predictor import predict_component_rules, predict_components_batch_rules, reset_engine


class TestModels:
    """Test data model classes."""

    def test_condition_evaluate_gte(self):
        c = Condition(feature="Cr", operator=">=", threshold=5.0)
        assert c.evaluate(5.0) is True
        assert c.evaluate(6.0) is True
        assert c.evaluate(4.9) is False

    def test_condition_evaluate_lte(self):
        c = Condition(feature="Cr", operator="<=", threshold=5.0)
        assert c.evaluate(5.0) is True
        assert c.evaluate(4.0) is True
        assert c.evaluate(5.1) is False

    def test_condition_to_dict_from_dict(self):
        c = Condition(feature="Ni", operator=">=", threshold=2.5)
        d = c.to_dict()
        c2 = Condition.from_dict(d)
        assert c2.feature == "Ni"
        assert c2.operator == ">="
        assert c2.threshold == 2.5

    def test_rule_evaluate_all_conditions_match(self):
        rule = Rule(
            id="test_rule",
            conditions=[
                Condition("Cr", ">=", 5.0),
                Condition("Ni", "<=", 10.0),
            ],
            prediction="TestClass",
        )
        assert rule.evaluate({"Cr": 6.0, "Ni": 8.0}) is True

    def test_rule_evaluate_one_condition_fails(self):
        rule = Rule(
            id="test_rule",
            conditions=[
                Condition("Cr", ">=", 5.0),
                Condition("Ni", "<=", 10.0),
            ],
            prediction="TestClass",
        )
        assert rule.evaluate({"Cr": 6.0, "Ni": 11.0}) is False

    def test_rule_missing_feature_defaults_zero(self):
        rule = Rule(
            id="test_rule",
            conditions=[Condition("Cr", ">=", 5.0)],
            prediction="TestClass",
        )
        # Missing Cr defaults to 0.0, which is < 5.0
        assert rule.evaluate({}) is False

    def test_rule_specificity(self):
        rule = Rule(
            id="test",
            conditions=[Condition("A", ">=", 1), Condition("B", ">=", 2)],
            prediction="X",
        )
        assert rule.specificity == 2

    def test_rule_to_dict_from_dict(self):
        rule = Rule(
            id="r1",
            conditions=[Condition("Cr", ">=", 5.0)],
            prediction="Class1",
            confidence=0.9,
            support=50,
            validation_accuracy=0.85,
            priority=100,
            description="Test rule",
        )
        d = rule.to_dict()
        r2 = Rule.from_dict(d)
        assert r2.id == "r1"
        assert r2.prediction == "Class1"
        assert r2.confidence == 0.9
        assert len(r2.conditions) == 1

    def test_prediction_result_no_match(self):
        result = PredictionResult(
            prediction="Unknown",
            confidence=0.0,
            status="no_match",
        )
        assert result.prediction == "Unknown"
        assert result.status == "no_match"

    def test_ruleset_to_dict_from_dict(self):
        rule = Rule(
            id="r1",
            conditions=[Condition("Cr", ">=", 5.0)],
            prediction="Class1",
            confidence=0.9,
        )
        rs = RuleSet(
            version="1.0.0",
            generated_at="2024-01-01T00:00:00",
            dataset_hash="abc123",
            algorithm="test",
            validation_score=0.9,
            rules_count=1,
            rules=[rule],
        )
        d = rs.to_dict()
        rs2 = RuleSet.from_dict(d)
        assert rs2.version == "1.0.0"
        assert len(rs2.rules) == 1
        assert rs2.rules[0].prediction == "Class1"


class TestPreprocessing:
    """Test preprocessing utilities."""

    def test_validate_input_normalizes(self):
        result = validate_input({"Cr": 5.0, "Unknown_Element": 99.0})
        assert result["Cr"] == 5.0
        assert "Unknown_Element" not in result
        # All feature columns present
        assert set(result.keys()) == set(FEATURE_COLUMNS)

    def test_validate_input_missing_defaults_to_zero(self):
        result = validate_input({})
        for col in FEATURE_COLUMNS:
            assert result[col] == 0.0

    def test_validate_input_handles_non_numeric(self):
        result = validate_input({"Cr": "5.0", "Ni": "N/A", "Mo": None})
        assert result["Cr"] == 5.0
        assert result["Ni"] == 0.0
        assert result["Mo"] == 0.0

    def test_load_csv_data(self):
        data_path = Path(__file__).parent.parent / "data" / "synthetic_eds_data.csv"
        if data_path.exists():
            data = load_csv_data(data_path)
            assert len(data) == 3582
            assert extract_target(data[0]) != ""

    def test_stratified_split_preserves_all_samples(self):
        data_path = Path(__file__).parent.parent / "data" / "synthetic_eds_data.csv"
        if data_path.exists():
            data = load_csv_data(data_path)
            train, val, test = stratified_split(data)
            assert len(train) + len(val) + len(test) == len(data)

    def test_feature_columns_count(self):
        # 18 features (19 original minus Cl which is constant)
        assert len(FEATURE_COLUMNS) == 18


class TestEngine:
    """Test the production rule engine."""

    def test_engine_loads(self):
        engine = RuleEngine()
        assert engine.rules_count == 36
        assert len(engine.classes) == 36

    def test_engine_predict_match(self):
        engine = RuleEngine()
        # CRI Injector Body is uniquely identified by Pb
        result = engine.predict({"Pb": 3.0, "Cr": 1.5, "Mn": 0.3})
        assert result.prediction == "CRI Injector Body"
        assert result.confidence > 0.0
        assert result.status in ("matched", "low_confidence")
        assert result.rule_id is not None

    def test_engine_predict_no_match(self):
        engine = RuleEngine()
        # Very unusual composition that matches no rules
        result = engine.predict({"Al": 99.0})
        assert result.prediction == "Unknown"
        assert result.status == "no_match"
        assert result.confidence == 0.0

    def test_engine_predict_missing_features_default_zero(self):
        engine = RuleEngine()
        result = engine.predict({})
        # Either no_match or a match with very broad rules
        assert result.status in ("no_match", "matched", "low_confidence")

    def test_engine_conflict_resolution_deterministic(self):
        engine = RuleEngine()
        input_data = {"Cr": 4.5, "Mo": 5.0, "V": 2.2, "W": 7.5, "Ni": 0.3}
        # Run prediction twice - should be identical
        r1 = engine.predict(input_data)
        r2 = engine.predict(input_data)
        assert r1.prediction == r2.prediction
        assert r1.rule_id == r2.rule_id
        assert r1.confidence == r2.confidence

    def test_engine_custom_threshold(self):
        engine = RuleEngine(confidence_threshold=0.99)
        result = engine.predict({"Pb": 3.0, "Cr": 1.5, "Mn": 0.3})
        # With very high threshold, may be low_confidence
        if result.confidence < 0.99 and result.status != "no_match":
            assert result.status == "low_confidence"

    def test_engine_explain_prediction(self):
        engine = RuleEngine()
        result = engine.predict({"Pb": 3.0, "Cr": 1.5, "Mn": 0.3})
        explanation = engine.explain_prediction(result)
        assert "Prediction:" in explanation
        assert "Confidence:" in explanation

    def test_engine_batch_predict(self):
        engine = RuleEngine()
        samples = [
            {"Pb": 3.0, "Cr": 1.5},
            {"Cr": 4.5, "Mo": 5.0, "V": 2.2, "W": 7.5, "Ni": 0.3},
        ]
        results = engine.predict_batch(samples)
        assert len(results) == 2
        assert all(isinstance(r, PredictionResult) for r in results)

    def test_engine_get_rules_for_class(self):
        engine = RuleEngine()
        rules = engine.get_rules_for_class("CRI Injector Body")
        assert len(rules) >= 1
        assert all(r.prediction == "CRI Injector Body" for r in rules)


class TestPredictor:
    """Test the integration predictor module."""

    def setup_method(self):
        reset_engine()

    def test_predict_component_rules(self):
        result = predict_component_rules({"Pb": 3.0, "Cr": 1.5, "Mn": 0.3})
        assert "prediction" in result
        assert "confidence" in result
        assert "rule_id" in result
        assert "status" in result
        assert "matched_conditions" in result
        assert "explanation" in result
        assert result["model_type"] == "rule_engine"

    def test_predict_component_rules_no_match(self):
        result = predict_component_rules({"Al": 99.0})
        assert result["prediction"] == "Unknown"
        assert result["status"] == "no_match"

    def test_predict_components_batch_rules(self):
        spectra = [{"Pb": 3.0}, {"Cr": 4.5, "Ni": 0.3}]
        results = predict_components_batch_rules(spectra)
        assert len(results) == 2
        assert all(isinstance(r, dict) for r in results)


class TestRulesJson:
    """Test the generated rules.json file."""

    def test_rules_json_valid(self):
        rules_path = Path(__file__).parent.parent / "rule_engine" / "rules" / "rules.json"
        with open(rules_path) as f:
            data = json.load(f)
        assert "version" in data
        assert "rules" in data
        assert data["rules_count"] == len(data["rules"])

    def test_rules_json_covers_all_classes(self):
        rules_path = Path(__file__).parent.parent / "rule_engine" / "rules" / "rules.json"
        with open(rules_path) as f:
            data = json.load(f)
        classes = set(r["prediction"] for r in data["rules"])
        assert len(classes) == 36

    def test_each_rule_has_required_fields(self):
        rules_path = Path(__file__).parent.parent / "rule_engine" / "rules" / "rules.json"
        with open(rules_path) as f:
            data = json.load(f)
        for rule in data["rules"]:
            assert "id" in rule
            assert "conditions" in rule
            assert "prediction" in rule
            assert "confidence" in rule
            assert "support" in rule
            assert "validation_accuracy" in rule
            assert "priority" in rule
            assert "description" in rule
            assert len(rule["conditions"]) > 0
            for cond in rule["conditions"]:
                assert "feature" in cond
                assert "operator" in cond
                assert "threshold" in cond
