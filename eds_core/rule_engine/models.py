"""
rule_engine/models.py
=====================
Data classes for the rule-based prediction engine.
All classes use stdlib dataclasses - no external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Condition:
    """A single condition in a rule: feature op threshold."""
    feature: str
    operator: str  # ">=", "<=", ">", "<", "==", "!="
    threshold: float

    def evaluate(self, value: float) -> bool:
        """Evaluate this condition against a value."""
        if self.operator == ">=":
            return value >= self.threshold
        elif self.operator == "<=":
            return value <= self.threshold
        elif self.operator == ">":
            return value > self.threshold
        elif self.operator == "<":
            return value < self.threshold
        elif self.operator == "==":
            return value == self.threshold
        elif self.operator == "!=":
            return value != self.threshold
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {"feature": self.feature, "operator": self.operator, "threshold": self.threshold}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Condition":
        return cls(feature=d["feature"], operator=d["operator"], threshold=float(d["threshold"]))


@dataclass
class Rule:
    """
    A prediction rule with conditions, prediction target, and quality metrics.

    Attributes:
        id: Unique rule identifier (e.g., "rule_001_armature_bolt")
        conditions: List of conditions that must ALL be true for the rule to fire
        prediction: The class name predicted when the rule fires
        confidence: Confidence score (0.0 to 1.0) based on training data support
        support: Number of training samples covered by this rule
        validation_accuracy: Accuracy on validation set for this rule
        priority: Priority for conflict resolution (higher = preferred)
        description: Human-readable description of the rule
    """
    id: str
    conditions: List[Condition]
    prediction: str
    confidence: float = 0.0
    support: int = 0
    validation_accuracy: float = 0.0
    priority: int = 0
    description: str = ""

    def evaluate(self, features: Dict[str, float]) -> bool:
        """Return True if ALL conditions match the given features."""
        for cond in self.conditions:
            value = features.get(cond.feature, 0.0)
            if not cond.evaluate(value):
                return False
        return True

    @property
    def specificity(self) -> int:
        """Number of conditions - more specific rules have more conditions."""
        return len(self.conditions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "conditions": [c.to_dict() for c in self.conditions],
            "prediction": self.prediction,
            "confidence": self.confidence,
            "support": self.support,
            "validation_accuracy": self.validation_accuracy,
            "priority": self.priority,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Rule":
        conditions = [Condition.from_dict(c) for c in d["conditions"]]
        return cls(
            id=d["id"],
            conditions=conditions,
            prediction=d["prediction"],
            confidence=float(d.get("confidence", 0.0)),
            support=int(d.get("support", 0)),
            validation_accuracy=float(d.get("validation_accuracy", 0.0)),
            priority=int(d.get("priority", 0)),
            description=d.get("description", ""),
        )


@dataclass
class RuleMatch:
    """A single rule that matched during evaluation."""
    rule: Rule
    matched_conditions: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule.id,
            "prediction": self.rule.prediction,
            "confidence": self.rule.confidence,
            "validation_accuracy": self.rule.validation_accuracy,
            "priority": self.rule.priority,
            "matched_conditions": self.matched_conditions,
        }


@dataclass
class PredictionResult:
    """
    Result of a rule engine prediction.

    Attributes:
        prediction: Predicted class name (or "Unknown" if no match)
        confidence: Confidence of the prediction
        rule_id: ID of the rule that fired (or None)
        matched_conditions: List of conditions that matched
        status: "matched", "low_confidence", "no_match", "fallback"
        all_matches: All rules that matched (for debugging/comparison)
    """
    prediction: str
    confidence: float
    rule_id: Optional[str] = None
    matched_conditions: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "no_match"
    all_matches: List[RuleMatch] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction": self.prediction,
            "confidence": self.confidence,
            "rule_id": self.rule_id,
            "matched_conditions": self.matched_conditions,
            "status": self.status,
            "num_matches": len(self.all_matches),
        }

    def __repr__(self) -> str:
        return (
            f"PredictionResult(prediction='{self.prediction}', "
            f"confidence={self.confidence:.4f}, "
            f"rule_id='{self.rule_id}', "
            f"status='{self.status}')"
        )


@dataclass
class RuleSet:
    """
    A versioned collection of rules with metadata.

    Attributes:
        version: Semantic version string
        generated_at: ISO timestamp of generation
        dataset_hash: SHA256 hash of the training data for reproducibility
        algorithm: Algorithm used to generate rules
        validation_score: Overall accuracy on validation set
        rules_count: Number of rules in the set
        rules: List of Rule objects
        metadata: Additional metadata (feature list, class list, etc.)
    """
    version: str
    generated_at: str
    dataset_hash: str
    algorithm: str
    validation_score: float
    rules_count: int
    rules: List[Rule]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "dataset_hash": self.dataset_hash,
            "algorithm": self.algorithm,
            "validation_score": self.validation_score,
            "rules_count": self.rules_count,
            "rules": [r.to_dict() for r in self.rules],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RuleSet":
        rules = [Rule.from_dict(r) for r in d["rules"]]
        return cls(
            version=d["version"],
            generated_at=d["generated_at"],
            dataset_hash=d["dataset_hash"],
            algorithm=d["algorithm"],
            validation_score=float(d["validation_score"]),
            rules_count=int(d["rules_count"]),
            rules=rules,
            metadata=d.get("metadata", {}),
        )
