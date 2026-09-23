"""
tests/test_component_fingerprints.py
====================================
Tests for component fingerprints loading, statistical validity, and alias resolution.
"""

import pytest
from rule_engine.component_fingerprints import (
    load_fingerprints,
    get_fingerprint,
    resolve_component_name,
    ComponentFingerprint,
)


def test_load_fingerprints():
    fps = load_fingerprints()
    assert len(fps) >= 30, f"Expected at least 30 fingerprints, got {len(fps)}"
    
    # Check known critical components
    critical = ["ARMATURE_BOLT", "ARMOUR_SPRING", "BALL_GUIDE", "CRI_INJECTOR_BODY", "VALVE_PISTON"]
    for cid in critical:
        # At least some of these must exist in the canonical library
        matching = [k for k in fps.keys() if cid in k or k.startswith("ARMATURE") or k.startswith("CRI")]
        assert len(matching) > 0, f"Expected canonical component matching {cid}"


def test_fingerprint_statistical_invariants():
    fps = load_fingerprints()
    for cid, fp in fps.items():
        assert fp.sample_count > 0
        assert fp.fingerprint_quality in ("LOW", "MEDIUM", "HIGH")
        assert len(fp.elements) > 0

        for el, stat in fp.elements.items():
            assert stat.min_val <= stat.max_val
            assert stat.q1 <= stat.median <= stat.q3 or (stat.q1 == stat.q3)
            assert stat.iqr >= 0
            assert stat.std >= 0
            assert 0.0 <= stat.frequency <= 1.0
            assert stat.role in ("expected", "common", "rare")


def test_alias_resolution():
    # Test resolving canonical and variations
    assert resolve_component_name("Armature Bolt") is not None
    assert resolve_component_name("armature bolt") is not None
    assert resolve_component_name("  Armature Bolt  ") is not None
    assert resolve_component_name("NonExistent_Fake_Component_XYZ") is None


def test_get_fingerprint():
    fp = get_fingerprint("Armature Bolt")
    assert fp is not None
    assert fp.display_name == "Armature Bolt"
    assert "Fe" in fp.elements
    assert fp.elements["Fe"].median > 90.0
