"""
tests/test_component_scoring.py
===============================
Unit tests for component-level scoring, distance calculation, ranking,
evidence sufficiency, and honest confidence calibration.
"""

import os
import pytest
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from rule_engine.normalize import normalize_spectrum
from rule_engine.component_fingerprints import load_fingerprints, get_fingerprint
from rule_engine.component_scoring import (
    score_component,
    rank_components,
    decide_component,
    ComponentScore,
)


def test_score_component_clean_match():
    # 100Cr6 bearing steel spectrum
    comp = {"Fe": 95.0, "Cr": 1.5, "Mn": 0.35, "Si": 0.30}
    norm_s = normalize_spectrum(comp)
    
    fp = get_fingerprint("Armature Bolt")
    assert fp is not None
    
    score = score_component(norm_s, fp)
    assert score.compatibility > 0.70
    assert "Fe" in score.matched_elements
    assert "Cr" in score.matched_elements
    assert score.evidence_sufficiency > 0.5


def test_score_component_foreign_element_penalty():
    # Fe spectrum with large foreign element (Zn 15%) which is unexpected in Armature Bolt
    comp = {"Fe": 80.0, "Zn": 15.0, "Cr": 1.5, "Mn": 0.35}
    norm_s = normalize_spectrum(comp)
    
    fp = get_fingerprint("Armature Bolt")
    score = score_component(norm_s, fp)
    
    clean_comp = {"Fe": 95.0, "Cr": 1.5, "Mn": 0.35, "Si": 0.30}
    clean_score = score_component(normalize_spectrum(clean_comp), fp)
    
    assert score.compatibility < clean_score.compatibility


def test_rank_components_order_and_bounds():
    comp = {"Fe": 95.0, "Cr": 1.5, "Mn": 0.35, "Si": 0.30}
    norm_s = normalize_spectrum(comp)
    
    ranked = rank_components(norm_s, candidate_family_ids=["F2"], top_n=5)
    assert len(ranked) > 0
    
    # Check descending order of compatibility
    for i in range(len(ranked) - 1):
        assert ranked[i].compatibility >= ranked[i + 1].compatibility
        
    # Check honest score limits (no 100% certainty, no negative)
    for c in ranked:
        assert 0.0 <= c.compatibility <= 0.95


def test_decide_component_logic():
    # Test clear leader separation -> identified
    c1 = ComponentScore("C1", "Comp 1", 0.85, ["F2"], 10, "HIGH", {}, ["Fe"], [], {}, 1.0)
    c2 = ComponentScore("C2", "Comp 2", 0.60, ["F2"], 8, "MEDIUM", {}, ["Fe"], [], {}, 0.9)
    dec, top = decide_component([c1, c2], min_margin=0.10)
    assert dec == "identified"
    assert top == c1

    # Test close tie -> ambiguous
    c3 = ComponentScore("C3", "Comp 3", 0.82, ["F2"], 10, "HIGH", {}, ["Fe"], [], {}, 1.0)
    dec_tie, _ = decide_component([c1, c3], min_margin=0.10)
    assert dec_tie == "ambiguous"

    # Test poor compatibility -> unknown
    c_low = ComponentScore("C4", "Comp 4", 0.15, ["F2"], 5, "LOW", {}, ["Fe"], [], {}, 0.3)
    dec_unknown, _ = decide_component([c_low], min_compatibility=0.30)
    assert dec_unknown == "unknown"


def test_no_confidence_inflation():
    from services.prediction.engine import run_prediction
    
    # Send a weak spectrum
    res = run_prediction(composition={"Fe": 99.0, "Cr": 0.2, "Si": 0.1})
    top_cand = res["topCandidate"]
    if top_cand:
        # Score must reflect actual compatibility, not artificially overridden to 95%
        assert top_cand["confidence"] == round(top_cand["compatibility"] * 100)
        assert top_cand["confidence"] < 100
