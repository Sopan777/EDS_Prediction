"""
tests/test_conflict_detection.py
================================
Unit tests for declared material metadata conflict detection.
"""

import pytest
from rule_engine.conflict_detector import detect_conflict, ConflictResult


def test_conflict_detected_when_mismatched():
    # Declared CuSn6 bronze, but measured as Low-alloy Cr bearing steel (F2)
    res = detect_conflict(
        declared_material="CuSn6 bronze",
        prediction_family_id="F2",
        prediction_family_label="Low-alloy Cr bearing steel",
    )
    assert res.has_conflict is True
    assert res.severity == "critical"
    assert "F2" in res.message


def test_no_conflict_when_matching():
    # Declared 100Cr6 and measured as F2
    res = detect_conflict(
        declared_material="100Cr6 bearing steel",
        prediction_family_id="F2",
        prediction_family_label="Low-alloy Cr bearing steel",
    )
    assert res.has_conflict is False
    assert res.severity == "none"


def test_no_conflict_when_undeclared():
    res = detect_conflict(
        declared_material=None,
        prediction_family_id="F4",
        prediction_family_label="Austenitic stainless steel 18/8",
    )
    assert res.has_conflict is False
    assert res.severity == "none"


def test_unmapped_material_warning():
    # Unknown trade name or exotic alloy string
    res = detect_conflict(
        declared_material="Inconel 718 Custom Spec",
        prediction_family_id="F5",
        prediction_family_label="Ni-base alloy",
    )
    assert res.has_conflict is False
    assert res.severity == "none"
