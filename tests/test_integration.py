"""
tests/test_integration.py
=========================
End-to-end integration tests for the rule engine.
Tests full prediction flow, batch predictions, predictor module,
and determinism.
Uses only pytest + stdlib (no pandas/numpy).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from rule_engine.engine import RuleEngine
from rule_engine.models import PredictionResult
from rule_engine.preprocessing import FEATURE_COLUMNS, validate_input, extract_features
from rule_engine.predictor import (
    predict_component_rules,
    predict_components_batch_rules,
    reset_engine,
)


class TestFullPredictionFlow:
    """Test the full flow from raw element dict through rule engine to result."""

    def test_raw_dict_to_prediction(self, rule_engine):
        """Test that a raw element dict gets correctly processed and predicted."""
        raw_input = {"Cr": 4.77, "Mo": 4.93, "V": 2.54, "W": 6.89, "Ni": 0.29, "Mn": 0.09}
        result = rule_engine.predict(raw_input)
        assert isinstance(result, PredictionResult)
        assert result.prediction == "Valve Piston"
        assert result.confidence > 0.0
        assert result.status == "matched"
        assert result.rule_id is not None

    def test_preprocessing_then_prediction(self, rule_engine):
        """Test validate_input followed by prediction gives same result."""
        raw_input = {"Cr": "4.77", "Mo": "4.93", "V": "2.54", "W": "6.89", "Mn": "0.09", "Ni": "0.29"}
        # The engine internally calls validate_input
        result = rule_engine.predict(raw_input)
        assert result.prediction == "Valve Piston"

    def test_end_to_end_with_string_values(self, rule_engine):
        """Test that string numeric values are handled end-to-end."""
        result = rule_engine.predict({"Ni": "81.83", "Al": "0.75", "Cr": "2.37"})
        assert result.prediction == "Clamping Saddle"

    def test_full_flow_no_match(self, rule_engine):
        """Test full flow when no rules match."""
        result = rule_engine.predict({"Al": 99.0})
        assert result.prediction == "Unknown"
        assert result.status == "no_match"
        assert result.confidence == 0.0
        assert result.rule_id is None


class TestBatchPrediction:
    """Test batch prediction with mixed results."""

    def test_batch_with_mixed_results(self, rule_engine):
        """Test batch prediction produces correct number of results."""
        samples = [
            {"Cr": 4.77, "Mo": 4.93, "V": 2.54, "W": 6.89},  # Valve Piston
            {"Ni": 81.83, "Al": 0.75, "Cr": 2.37},  # Clamping Saddle
            {"Al": 99.0},  # No match
            {"Cu": 45.09, "Au": 49.84, "K": 0.17},  # Blade Terminal
        ]
        results = rule_engine.predict_batch(samples)
        assert len(results) == 4
        assert all(isinstance(r, PredictionResult) for r in results)

    def test_batch_some_match_some_no_match(self, rule_engine):
        """Batch with valid and invalid inputs."""
        samples = [
            {"Cr": 4.77, "Mo": 4.93, "V": 2.54, "W": 6.89, "Mn": 0.09, "Ni": 0.29},  # Should match
            {},  # Likely no_match
            {"Al": 99.0},  # No match
        ]
        results = rule_engine.predict_batch(samples)
        # At least first should match
        assert results[0].prediction == "Valve Piston"
        # Empty/99 should be no_match
        assert results[2].prediction == "Unknown"

    def test_batch_empty_list(self, rule_engine):
        """Batch with empty list returns empty list."""
        results = rule_engine.predict_batch([])
        assert results == []

    def test_batch_single_item(self, rule_engine):
        """Batch with single item returns list of one result."""
        results = rule_engine.predict_batch([{"Zn": 0.2}])
        assert len(results) == 1
        assert isinstance(results[0], PredictionResult)


class TestPredictorIntegration:
    """Test the predictor.py integration module returns correct dict format."""

    def setup_method(self):
        reset_engine()

    def test_predict_component_rules_format(self):
        """predict_component_rules returns dict with expected keys."""
        result = predict_component_rules({"Cr": 4.77, "Mo": 4.93, "V": 2.54, "W": 6.89})
        assert isinstance(result, dict)
        expected_keys = {
            "prediction", "confidence", "rule_id", "status",
            "matched_conditions", "explanation", "model_type", "num_rules_matched"
        }
        assert set(result.keys()) == expected_keys

    def test_predict_component_rules_model_type(self):
        """model_type should always be 'rule_engine'."""
        result = predict_component_rules({"Cr": 5.0})
        assert result["model_type"] == "rule_engine"

    def test_predict_component_rules_prediction_string(self):
        """prediction should be a string."""
        result = predict_component_rules({"Pb": 0.22, "Cr": 0.3, "Mn": 0.72})
        assert isinstance(result["prediction"], str)

    def test_predict_component_rules_confidence_range(self):
        """confidence should be between 0 and 1."""
        result = predict_component_rules({"Cr": 4.77, "Mo": 4.93, "V": 2.54, "W": 6.89})
        assert 0.0 <= result["confidence"] <= 1.0

    def test_predict_components_batch_format(self):
        """Batch prediction returns list of dicts."""
        spectra = [
            {"Cr": 4.77, "Mo": 4.93, "V": 2.54, "W": 6.89},
            {"Ni": 81.83},
        ]
        results = predict_components_batch_rules(spectra)
        assert isinstance(results, list)
        assert len(results) == 2
        for r in results:
            assert isinstance(r, dict)
            assert "prediction" in r
            assert "model_type" in r
            assert r["model_type"] == "rule_engine"

    def test_predict_component_rules_explanation_is_string(self):
        """explanation field should be a string."""
        result = predict_component_rules({"Cr": 4.77, "Mo": 4.93, "V": 2.54, "W": 6.89})
        assert isinstance(result["explanation"], str)
        assert len(result["explanation"]) > 0


class TestResetEngine:
    """Test that reset_engine properly reloads."""

    def test_reset_then_predict(self):
        """After reset, predictions should still work."""
        reset_engine()
        result = predict_component_rules({"Cr": 4.77, "Mo": 4.93, "V": 2.54, "W": 6.89, "Mn": 0.09, "Ni": 0.29})
        assert result["prediction"] == "Valve Piston"

    def test_reset_creates_new_engine(self):
        """Reset should clear the cached engine."""
        # First call loads engine
        predict_component_rules({"Cr": 5.0})
        # Reset
        reset_engine()
        # Next call should load a new engine and still work
        result = predict_component_rules({"Ni": 81.83, "Al": 0.75, "Cr": 2.37})
        assert result["prediction"] == "Clamping Saddle"


class TestCustomConfidenceThreshold:
    """Test rule engine with custom confidence thresholds."""

    def test_high_threshold_flags_low_confidence(self):
        """Very high threshold should flag results as low_confidence."""
        engine = RuleEngine(confidence_threshold=0.9999)
        result = engine.predict({"Cr": 4.77, "Mo": 4.93, "V": 2.54, "W": 6.89})
        if result.status != "no_match":
            # If confidence < 0.9999, it should be low_confidence
            if result.confidence < 0.9999:
                assert result.status == "low_confidence"
            else:
                assert result.status == "matched"

    def test_zero_threshold_all_matched(self):
        """Zero threshold should make all matches 'matched' status."""
        engine = RuleEngine(confidence_threshold=0.0)
        result = engine.predict({"Cr": 4.77, "Mo": 4.93, "V": 2.54, "W": 6.89})
        if result.status != "no_match":
            assert result.status == "matched"

    def test_override_threshold_on_predict(self):
        """Per-call threshold override should work."""
        engine = RuleEngine(confidence_threshold=0.4)
        # Use per-call override with very high threshold
        result = engine.predict(
            {"Cr": 4.77, "Mo": 4.93, "V": 2.54, "W": 6.89},
            confidence_threshold=0.9999,
        )
        if result.status != "no_match" and result.confidence < 0.9999:
            assert result.status == "low_confidence"


class TestPredictionDeterminism:
    """Test that predictions are deterministic."""

    def test_same_input_same_output(self, rule_engine):
        """Same input must always produce the same prediction."""
        input_data = {"Cr": 4.77, "Mo": 4.93, "V": 2.54, "W": 6.89, "Ni": 0.29}
        results = [rule_engine.predict(input_data) for _ in range(10)]
        predictions = [r.prediction for r in results]
        confidences = [r.confidence for r in results]
        rule_ids = [r.rule_id for r in results]
        # All should be identical
        assert len(set(predictions)) == 1
        assert len(set(confidences)) == 1
        assert len(set(rule_ids)) == 1

    def test_separate_engines_same_result(self):
        """Two separate engine instances should give the same result."""
        engine1 = RuleEngine()
        engine2 = RuleEngine()
        input_data = {"Cu": 45.09, "Au": 49.84, "K": 0.17, "N": 0.88}
        r1 = engine1.predict(input_data)
        r2 = engine2.predict(input_data)
        assert r1.prediction == r2.prediction
        assert r1.confidence == r2.confidence
        assert r1.rule_id == r2.rule_id


class TestExplainPrediction:
    """Test explain_prediction output format."""

    def test_explain_matched_prediction(self, rule_engine):
        """Explanation for matched prediction should contain key info."""
        result = rule_engine.predict({"Cr": 4.77, "Mo": 4.93, "V": 2.54, "W": 6.89})
        explanation = rule_engine.explain_prediction(result)
        assert "Prediction:" in explanation
        assert "Confidence:" in explanation
        assert "Status:" in explanation
        assert "Rule:" in explanation
        assert "Matched conditions:" in explanation

    def test_explain_no_match(self, rule_engine):
        """Explanation for no_match should indicate no rules matched."""
        result = rule_engine.predict({"Al": 99.0})
        explanation = rule_engine.explain_prediction(result)
        assert "No rules matched" in explanation

    def test_explain_contains_actual_values(self, rule_engine):
        """Explanation should show actual element values."""
        result = rule_engine.predict({"Cr": 4.77, "Mo": 4.93, "V": 2.54, "W": 6.89})
        explanation = rule_engine.explain_prediction(result)
        assert "actual:" in explanation
