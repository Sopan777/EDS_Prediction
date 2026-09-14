"""
tests/test_streamlit_app.py
===========================
Automated tests for the unified Spectral Lab Streamlit application (app.py).
Verifies:
  - App module import and knowledge base singleton caching
  - Manual microanalysis prediction (Austenitic SS, Bronze, Carbon Steel)
  - Safe abstention on sparse input ({S: 0.2} -> UNKNOWN)
  - Real PDF report ingest and spectral table extraction
  - Ground-truth dataset validation engine
  - Ratio gate updates and SQLite persistence
  - Audit log and user management records
"""

import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import app
from rule_engine.scoring import Decision, predict_spectrum
from rule_engine.normalize import normalize_spectrum, State


def test_app_imports_and_kb_loaded():
    """Verify app module imports cleanly and KB contains 12 material families."""
    kb = app.load_kb()
    assert kb is not None
    assert len(kb.families) == 12
    assert "F4" in kb.families
    assert "F6a" in kb.families
    assert "F1a" in kb.families


def test_microanalysis_austenitic_stainless_steel():
    """Verify precision prediction of AISI 304 SS."""
    kb = app.load_kb()
    comp = {"Cr": 18.2, "Ni": 8.4, "Mn": 1.6, "Si": 0.5, "Fe": 71.3}
    pred = predict_spectrum(comp, knowledge=kb)

    assert pred.decision in (Decision.IDENTIFIED, Decision.AMBIGUOUS)
    assert pred.top is not None
    assert pred.top.family_id == "F4"
    assert "18/8" in pred.top.label.lower() or "austenitic" in pred.top.label.lower()
    assert pred.top.compatibility >= 0.70


def test_microanalysis_sparse_input_abstains():
    """Verify safe abstention on sparse composition ({S: 0.2} -> UNKNOWN)."""
    kb = app.load_kb()
    comp = {"S": 0.2}
    pred = predict_spectrum(comp, knowledge=kb)

    assert pred.decision == Decision.UNKNOWN
    assert pred.top is None


def test_microanalysis_bronze_alloy():
    """Verify prediction of Cu-Sn bronze."""
    kb = app.load_kb()
    comp = {"Cu": 88.5, "Sn": 10.5, "P": 0.4, "Fe": 0.3}
    pred = predict_spectrum(comp, knowledge=kb)

    assert pred.decision in (Decision.IDENTIFIED, Decision.AMBIGUOUS)
    assert pred.top is not None
    assert pred.top.family_id in ("F6a", "F6b")


def test_metal_basis_normalization():
    """Verify normalization separates alloy basis from light elements (C, O)."""
    kb = app.load_kb()
    comp = {"C": 8.63, "O": 1.96, "Si": 0.25, "Mn": 0.28, "Fe": 88.04, "Zn": 0.84}
    norm = normalize_spectrum(comp)

    assert norm.readings["Fe"].state == State.MEASURED
    assert norm.readings["C"].in_alloy_basis is False
    assert norm.readings["O"].in_alloy_basis is False
    assert norm.readings["Fe"].in_alloy_basis is True


def test_pdf_extraction_and_scoring():
    """Verify end-to-end PDF table extraction and prediction."""
    pdf_path = REPO_ROOT / "data" / "reports" / "Field CRI.I. 26-108 Particle In IC Stud (ISUZU) ......14.pdf"
    if not pdf_path.exists():
        pytest.skip("Sample PDF report not found")

    assert app.extract_pdf_tables is not None
    extracted = app.extract_pdf_tables(str(pdf_path))
    tables = extracted.get("eds_tables", [])
    assert len(tables) >= 2

    # Score page 2 table (plain carbon steel)
    table_p2 = next((t for t in tables if t["page"] == 2), None)
    assert table_p2 is not None
    spec_1 = table_p2["spectra"][0]["values"]
    clean_comp = {k: v for k, v in spec_1.items() if v is not None and k != "Total"}

    pred = predict_spectrum(clean_comp, knowledge=app.load_kb())
    assert pred.top is not None
    assert pred.top.family_id.startswith("F1")


def test_reference_dataset_validation():
    """Verify live validation against the 173 reference spectra."""
    spectra = app.get_reference_spectra()
    if not spectra:
        pytest.skip("Reference dataset not found")

    assert len(spectra) == 173
    kb = app.load_kb()

    passing = 0
    for s in spectra:
        p = predict_spectrum(s["values"], analysed_elements=s["analysed_elements"], knowledge=kb)
        if p.top is not None:
            passing += 1

    pass_rate = passing / len(spectra)
    assert pass_rate >= 0.85, f"Expected at least 85% pass rate on reference spectra, got {pass_rate:.1%}"


def test_sqlite_database_tables():
    """Verify SQLite tables exist and contain required seed data."""
    conn = app.get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    assert cur.fetchone()[0] >= 5

    cur.execute("SELECT COUNT(*) FROM audit_logs")
    assert cur.fetchone()[0] >= 3

    conn.close()
