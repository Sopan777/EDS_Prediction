"""
rule_engine/predictor.py
========================
Integration module providing predict_component_rules() and
predict_components_batch_rules() functions that match the signature pattern
of the existing predictor.py, so the rule engine can be used as a drop-in
alternative prediction backend.

Pure Python stdlib - no external dependencies.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from rule_engine.engine import RuleEngine
from rule_engine.models import PredictionResult

# Import config values so changing config.py changes default behavior
from config import RULES_FILE, RULE_CONFIDENCE_THRESHOLD

# --------------------------------------------------------------------------
# Cached engine instances - keyed by resolved path, reused across calls.
# --------------------------------------------------------------------------

_ENGINE_CACHE: Dict[str, RuleEngine] = {}


def _get_engine(rules_path: Optional[str] = None) -> RuleEngine:
    """Get or create a cached RuleEngine instance for the given rules path."""
    if rules_path:
        resolved = str(Path(rules_path).resolve())
    else:
        resolved = str(Path(RULES_FILE).resolve())

    if resolved not in _ENGINE_CACHE:
        if rules_path:
            _ENGINE_CACHE[resolved] = RuleEngine(rules_path=rules_path)
        else:
            _ENGINE_CACHE[resolved] = RuleEngine()

    return _ENGINE_CACHE[resolved]


def predict_component_rules(
    eds_values: Dict[str, Any],
    confidence_threshold: float = RULE_CONFIDENCE_THRESHOLD,
    rules_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Predict the most likely component for one EDS spectrum using rules.

    This function mirrors the interface pattern of predictor.predict_component()
    but uses the rule-based engine instead of ML models.

    Args:
        eds_values: Dict of {element: weight_percent} - e.g. {"Cr": 12.5, "Ni": 8.2}.
            Missing elements are treated as 0.0.
        confidence_threshold: Minimum confidence for a full "matched" status.
            Below this, prediction is flagged as low confidence.
        rules_path: Optional path to a custom rules.json file.

    Returns:
        Dict with keys:
            - prediction: str (component name or "Unknown")
            - confidence: float (0.0 to 1.0)
            - rule_id: str or None
            - status: str ("matched", "low_confidence", "no_match")
            - matched_conditions: list of condition dicts
            - explanation: str (human-readable explanation)
            - model_type: str ("rule_engine")
    """
    engine = _get_engine(rules_path)
    result = engine.predict(eds_values, confidence_threshold=confidence_threshold)

    return {
        "prediction": result.prediction,
        "confidence": result.confidence,
        "rule_id": result.rule_id,
        "status": result.status,
        "matched_conditions": result.matched_conditions,
        "explanation": engine.explain_prediction(result),
        "model_type": "rule_engine",
        "num_rules_matched": len(result.all_matches),
    }


def predict_components_batch_rules(
    spectra: List[Dict[str, Any]],
    confidence_threshold: float = RULE_CONFIDENCE_THRESHOLD,
    rules_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Predict components for a batch of spectra using rules.

    Mirrors predictor.predict_components_batch() pattern.

    Args:
        spectra: List of {element: value} dicts.
        confidence_threshold: Minimum confidence threshold.
        rules_path: Optional path to a custom rules.json file.

    Returns:
        List of prediction result dicts (same format as predict_component_rules).
    """
    return [
        predict_component_rules(
            eds_values=spectrum,
            confidence_threshold=confidence_threshold,
            rules_path=rules_path,
        )
        for spectrum in spectra
    ]


def reset_engine() -> None:
    """Reset all cached engine instances (useful for testing or reloading rules)."""
    global _ENGINE_CACHE
    _ENGINE_CACHE = {}
