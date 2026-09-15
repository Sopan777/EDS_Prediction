"""
rule_engine
===========
Pure-stdlib rule-based prediction engine for EDS component classification.
No external dependencies required - uses only Python standard library modules.
"""

from rule_engine.engine import RuleEngine
from rule_engine.models import Rule, RuleSet, RuleMatch, PredictionResult

__all__ = ["RuleEngine", "Rule", "RuleSet", "RuleMatch", "PredictionResult"]
