"""
rule_engine/engine.py
=====================
Production rule engine for EDS component prediction.
Loads rules from JSON, evaluates them against input element compositions,
resolves conflicts deterministically, and returns structured predictions.

Pure Python stdlib - no external dependencies.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from rule_engine.models import Condition, Rule, RuleMatch, RuleSet, PredictionResult
from rule_engine.preprocessing import FEATURE_COLUMNS, validate_input

# Import config values so that changing config.py changes engine behavior
from config import RULES_FILE, RULE_CONFIDENCE_THRESHOLD

# Default path to rules file (from config.py, can be overridden per-instance)
_DEFAULT_RULES_PATH = Path(RULES_FILE)

# Default confidence threshold (from config.py)
_DEFAULT_CONFIDENCE_THRESHOLD = RULE_CONFIDENCE_THRESHOLD


class RuleEngine:
    """
    Production rule engine for EDS component classification.

    Usage:
        engine = RuleEngine()  # loads default rules.json
        result = engine.predict({"Cr": 4.5, "Mo": 5.0, "V": 2.2, "W": 7.5})
        print(result.prediction, result.confidence)

    Conflict Resolution Strategy (deterministic):
        1. Highest validation_accuracy
        2. Highest confidence
        3. Highest support
        4. Most specific (most conditions)
        5. Alphabetical rule_id (final tiebreaker)
    """

    def __init__(
        self,
        rules_path: Optional[str | Path] = None,
        confidence_threshold: float = _DEFAULT_CONFIDENCE_THRESHOLD,
    ):
        """
        Initialize the rule engine.

        Args:
            rules_path: Path to rules.json. Defaults to rule_engine/rules/rules.json.
            confidence_threshold: Minimum confidence for a "matched" status.
                Below this, status is "low_confidence".
        """
        self.confidence_threshold = confidence_threshold
        self._rules_path = Path(rules_path) if rules_path else _DEFAULT_RULES_PATH
        self._ruleset: Optional[RuleSet] = None
        self._rules: List[Rule] = []
        self._loaded = False

        # Load rules on initialization
        self._load_rules()

    def _load_rules(self) -> None:
        """Load and parse the rules JSON file."""
        if not self._rules_path.exists():
            raise FileNotFoundError(
                f"Rules file not found: {self._rules_path}. "
                f"Run `python training/train_rules.py` to generate it."
            )

        with open(self._rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._ruleset = RuleSet.from_dict(data)
        self._rules = self._ruleset.rules
        self._loaded = True

    @property
    def ruleset(self) -> Optional[RuleSet]:
        """The loaded RuleSet, or None if not loaded."""
        return self._ruleset

    @property
    def rules_count(self) -> int:
        """Number of loaded rules."""
        return len(self._rules)

    @property
    def classes(self) -> List[str]:
        """List of unique classes covered by the rules."""
        return sorted(set(r.prediction for r in self._rules))

    def predict(
        self,
        eds_values: Dict[str, Any],
        confidence_threshold: Optional[float] = None,
    ) -> PredictionResult:
        """
        Predict the component class for a given set of element values.

        Args:
            eds_values: Dict of {element_name: weight_percent} values.
                Missing elements default to 0.0.
            confidence_threshold: Override the instance-level threshold.

        Returns:
            PredictionResult with prediction, confidence, rule_id, status.
        """
        if not self._loaded:
            self._load_rules()

        threshold = confidence_threshold if confidence_threshold is not None else self.confidence_threshold

        # Validate and normalize input
        features = validate_input(eds_values)

        # Evaluate all rules against the input
        matches: List[RuleMatch] = []
        for rule in self._rules:
            if rule.evaluate(features):
                matched_conds = [
                    {"feature": c.feature, "operator": c.operator,
                     "threshold": c.threshold, "actual_value": features.get(c.feature, 0.0)}
                    for c in rule.conditions
                ]
                matches.append(RuleMatch(rule=rule, matched_conditions=matched_conds))

        # No matches - return no_match result
        if not matches:
            return PredictionResult(
                prediction="Unknown",
                confidence=0.0,
                rule_id=None,
                matched_conditions=[],
                status="no_match",
                all_matches=[],
            )

        # Resolve conflicts - pick the best match
        best_match = self._resolve_conflicts(matches)

        # Determine status based on confidence
        if best_match.rule.confidence < threshold:
            status = "low_confidence"
        else:
            status = "matched"

        return PredictionResult(
            prediction=best_match.rule.prediction,
            confidence=best_match.rule.confidence,
            rule_id=best_match.rule.id,
            matched_conditions=best_match.matched_conditions,
            status=status,
            all_matches=matches,
        )

    def predict_batch(
        self,
        samples: List[Dict[str, Any]],
        confidence_threshold: Optional[float] = None,
    ) -> List[PredictionResult]:
        """
        Predict components for a batch of samples.

        Args:
            samples: List of {element: value} dicts.
            confidence_threshold: Override the instance-level threshold.

        Returns:
            List of PredictionResult objects, one per sample.
        """
        return [self.predict(s, confidence_threshold=confidence_threshold) for s in samples]

    def _resolve_conflicts(self, matches: List[RuleMatch]) -> RuleMatch:
        """
        Resolve conflicts between multiple matching rules.

        Strategy (deterministic):
            1. Highest validation_accuracy
            2. Highest confidence (tiebreaker)
            3. Highest support (tiebreaker)
            4. Most specific - most conditions (tiebreaker)
            5. Alphabetical rule_id (final tiebreaker for full determinism)
        """
        def sort_key(match: RuleMatch):
            r = match.rule
            return (
                r.validation_accuracy,
                r.confidence,
                r.support,
                r.specificity,
                # Reverse alphabetical so that sorted() descending picks first alpha
                # We negate by using a trick: sort ascending by reversed string
            )

        # Sort by quality metrics (descending) then by rule_id (ascending) for determinism
        sorted_matches = sorted(
            matches,
            key=lambda m: (
                -m.rule.validation_accuracy,
                -m.rule.confidence,
                -m.rule.support,
                -m.rule.specificity,
                m.rule.id,
            ),
        )

        return sorted_matches[0]

    def get_rules_for_class(self, class_name: str) -> List[Rule]:
        """Get all rules that predict a given class."""
        return [r for r in self._rules if r.prediction == class_name]

    def explain_prediction(self, result: PredictionResult) -> str:
        """Generate a human-readable explanation for a prediction result."""
        if result.status == "no_match":
            return "No rules matched the input. The composition does not match any known component pattern."

        lines = [
            f"Prediction: {result.prediction}",
            f"Confidence: {result.confidence:.2%}",
            f"Status: {result.status}",
            f"Rule: {result.rule_id}",
            "",
            "Matched conditions:",
        ]

        for cond in result.matched_conditions:
            lines.append(
                f"  - {cond['feature']} {cond['operator']} {cond['threshold']:.2f} "
                f"(actual: {cond['actual_value']:.2f})"
            )

        if result.status == "low_confidence":
            lines.append("")
            lines.append("WARNING: Low confidence prediction - manual review recommended.")

        if len(result.all_matches) > 1:
            lines.append("")
            lines.append(f"Note: {len(result.all_matches)} rules matched. "
                         f"Best rule selected by conflict resolution.")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"RuleEngine(rules={self.rules_count}, "
            f"classes={len(self.classes)}, "
            f"threshold={self.confidence_threshold})"
        )
