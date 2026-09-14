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


import database

def test_sqlite_database_tables():
    """Verify SQLite tables exist and contain required seed data."""
    conn = database.get_connection()
    cur = conn.cursor()

    # Tables exist
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    assert {"reports", "audit_logs", "ratio_gates", "users", "alloy_presets"}.issubset(tables)

    # Lead Metallurgist administrator seeded
    cur.execute("SELECT COUNT(*) FROM users")
    assert cur.fetchone()[0] >= 1

    # Standard metallurgical presets seeded
    cur.execute("SELECT COUNT(*) FROM alloy_presets")
    assert cur.fetchone()[0] >= 5

    conn.close()


def test_database_reports_crud():
    """Verify full CRUD lifecycle for official analysis reports."""
    sample_id = "TEST-PARTICLE-999"
    raw_comp = {"Cr": 18.0, "Ni": 8.0, "Fe": 74.0}
    norm_comp = [
        {"element": "Fe", "raw_wt": 74.0, "metal_wt": 74.0, "state": "MEASURED", "basis": True},
        {"element": "Cr", "raw_wt": 18.0, "metal_wt": 18.0, "state": "MEASURED", "basis": True},
        {"element": "Ni", "raw_wt": 8.0, "metal_wt": 8.0, "state": "MEASURED", "basis": True},
    ]

    # 1. Save Report
    report_id = database.save_report(
        title="Test Austenitic Verification",
        sample_id=sample_id,
        analyst_id="usr-admin",
        analyst_name="Lead Metallurgist",
        source_type="Manual Microanalysis",
        raw_composition=raw_comp,
        normalized_composition=norm_comp,
        decision="identified",
        family_id="F4",
        family_label="Austenitic Stainless Steel (304 / 316)",
        grade_hint="AISI 304 / 1.4301",
        compatibility_pct=96.5,
        candidates=["Valve needle", "Metering plate"],
        caveats=[],
        lot_number="LOT-2026-X",
        customer="Automotive OEM",
        analyst_notes="Clean particle with standard stoichiometric 18/8 balance.",
        status="Completed",
    )
    assert report_id.startswith("RPT-")

    # 2. Get Reports list & filter
    reports = database.get_reports(search_query=sample_id)
    assert len(reports) >= 1
    found = next((r for r in reports if r["id"] == report_id), None)
    assert found is not None
    assert found["sample_id"] == sample_id
    assert found["family_id"] == "F4"
    assert found["compatibility_pct"] == 96.5
    assert found["lot_number"] == "LOT-2026-X"

    # 3. Get Report by ID
    single = database.get_report_by_id(report_id)
    assert single is not None
    assert single["title"] == "Test Austenitic Verification"
    assert single["raw_composition"]["Cr"] == 18.0

    # 4. Update Status
    success = database.update_report_status(report_id, "Approved", user_name="Quality Director")
    assert success is True
    updated = database.get_report_by_id(report_id)
    assert updated["status"] == "Approved"

    # 5. Delete Report
    del_success = database.delete_report(report_id, user_name="Quality Director")
    assert del_success is True
    assert database.get_report_by_id(report_id) is None


def test_database_ratio_gates_lifecycle():
    """Verify persisting, retrieving, and resetting family ratio gates."""
    family_id = "F4"
    custom_gates = [
        {
            "id": "gate-test-cr-ni",
            "name": "Cr / Ni Stoichiometry",
            "numerator": "Cr",
            "denominator": "Ni",
            "min": 1.8,
            "max": 2.5,
            "rationale": "Tightened bounds for specialized test validation.",
            "enabled": True,
        }
    ]

    # Save
    database.save_gates_for_family(family_id, custom_gates, user_name="Lead Metallurgist")

    # Retrieve
    stored = database.get_gates_for_family(family_id)
    assert stored is not None
    assert len(stored) == 1
    assert stored[0]["name"] == "Cr / Ni Stoichiometry"
    assert stored[0]["min"] == 1.8

    # Reset
    database.reset_gates_for_family(family_id, user_name="Lead Metallurgist")
    assert database.get_gates_for_family(family_id) is None


def test_database_user_and_audit_logging():
    """Verify user registration and audit trail recording."""
    # Register user
    user_id = database.add_user(
        name="Dr. Eleanor Vance",
        email="e.vance@spectrallab.io",
        role="Senior Metallurgist",
        department="Failure Analysis",
        permissions="Read & Calibrate",
        initials="EV",
    )
    assert user_id.startswith("usr-")

    users = database.get_users()
    assert any(u["id"] == user_id for u in users)

    # Log manual audit event
    audit_id = database.log_audit(
        user_id=user_id,
        user_name="Dr. Eleanor Vance",
        user_role="Senior Metallurgist",
        action="Calibrated SEM EDS detector gain",
        action_type="INSTRUMENT_CALIBRATION",
        details={"detector": "Oxford Aztec", "gain_offset_ev": 0.4},
        impact_type="positive",
    )
    assert audit_id.startswith("aud-")

    logs = database.get_audit_logs(action_type="INSTRUMENT_CALIBRATION")
    assert any(l["id"] == audit_id for l in logs)


def test_database_alloy_presets():
    """Verify official reference presets exist and custom presets can be added."""
    presets = database.get_presets()
    assert len(presets) >= 5
    preset_names = [p["name"] for p in presets]
    assert any("304" in name for name in preset_names)
    assert any("Bronze" in name for name in preset_names)

    new_id = database.add_preset(
        name="Custom Inconel 718",
        category="Superalloy",
        description="Nickel-chromium superalloy for high-temperature turbine blades",
        composition={"Ni": 52.5, "Cr": 19.0, "Fe": 18.5, "Nb": 5.1, "Mo": 3.0, "Ti": 0.9, "Al": 0.5},
        created_by="Lead Metallurgist",
    )
    assert new_id.startswith("preset-")

    refreshed = database.get_presets()
    assert any(p["id"] == new_id for p in refreshed)

