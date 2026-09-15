"""
tests/test_server_fixes.py
==========================
Regression tests validating the technical audit fixes in backend/server.py:
  1. Real compatibility scores returned (no artificial clamping to 95%).
  2. Candidate components contain real names from materials.json (no fabricated BOSCH-* part numbers).
  3. Real totalSpectra count reported (no n_spectra * 12 multiplier).
  4. /api/analyses GET endpoint returns historical analyses from SQLite.
  5. /api/sessions POST endpoint persists new particle sessions.
  6. Ratio gates saved to SQLite are injected into prediction scoring at runtime.
  7. /api/gates/validate returns real counts from reference spectra.
"""

import json
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.server import app, get_db_connection


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_compatibility_not_overridden_for_low_scores(client):
    """
    Audit fix #5.3: Ensure comp_pct is NOT overridden to 95 when compatibility < 70%.
    Composition with some stainless characteristics but borderline compatibility.
    """
    # A borderline composition
    payload = {
        "composition": {
            "Cr": 14.5,
            "Ni": 6.0,
            "Mn": 1.0,
            "Si": 0.5,
            "Fe": "Bal.",
        }
    }
    res = client.post("/api/analyze", json=payload)
    assert res.status_code == 200
    data = res.get_json()

    # The compatibility must equal round(data["compatibility"] * 100) exactly
    expected_pct = round(data["compatibility"] * 100)
    assert data["compatibilityPct"] == expected_pct, (
        f"Expected compatibilityPct to equal real calculation ({expected_pct}), "
        f"got {data['compatibilityPct']} (check for hardcoded 95 override)."
    )


def test_candidate_components_no_fabricated_part_numbers(client):
    """
    Audit fix #5.4: Ensure candidate components do NOT have fabricated
    BOSCH-F4-{initials}{len*3} part numbers.
    """
    res = client.get("/api/families/F4")
    assert res.status_code == 200
    data = res.get_json()

    for comp in data.get("candidateComponents", []):
        part_num = comp.get("partNumber", "")
        assert not part_num.startswith("BOSCH-"), (
            f"Found fabricated part number '{part_num}' in candidate components"
        )


def test_real_spectra_count_in_family_catalog(client):
    """
    Audit fix #5.5: Total spectra in family catalog must match materials.json n_spectra,
    not n_spectra * 12.
    """
    res = client.get("/api/families/F1a")
    assert res.status_code == 200
    data = res.get_json()

    # In materials.json, F1a has 61 spectra.
    # Previously, server multiplied 61 * 12 = 732.
    assert data["totalSpectra"] == 61, (
        f"Expected 61 real spectra for F1a, got {data['totalSpectra']} (check for *12 multiplier)"
    )


def test_analysis_history_endpoint(client):
    """
    Audit fix #5.12: GET /api/analyses returns historical analysis rows from SQLite.
    """
    # Run an analysis first to ensure at least one row exists
    payload = {
        "composition": {
            "Cr": 18.0,
            "Ni": 8.0,
            "Mn": 1.5,
            "Si": 0.5,
            "Fe": "Bal.",
        }
    }
    post_res = client.post("/api/analyze", json=payload)
    assert post_res.status_code == 200
    posted_id = post_res.get_json()["analysisId"]

    # Now query the listing endpoint
    res = client.get("/api/analyses")
    assert res.status_code == 200
    analyses = res.get_json()
    assert isinstance(analyses, list)
    assert len(analyses) >= 1

    # Verify the posted analysis is present
    ids = [a["id"] for a in analyses]
    assert posted_id in ids

    # Single detail endpoint
    detail_res = client.get(f"/api/analyses/{posted_id}")
    assert detail_res.status_code == 200
    detail = detail_res.get_json()
    assert detail["id"] == posted_id
    assert "Cr" in detail["composition"]


def test_sessions_endpoint(client):
    """
    Audit fix: POST /api/sessions creates a new particle scan session.
    """
    payload = {
        "particleId": "P-TEST-9999",
        "spectrometer": "Oxford Instruments Aztec (20 kV)",
        "description": "Filter basket debris sample",
        "createdBy": "Test Metallurgist",
    }
    res = client.post("/api/sessions", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "created"
    assert data["particleId"] == "P-TEST-9999"


def test_gate_injection_into_scoring(client):
    """
    Audit fix #6.4: Ratio gates saved to SQLite via PUT /api/gates/<fid>
    must be injected into scoring at predict time.
    """
    # 1. Standard Austenitic SS composition (normally identified as F4)
    comp = {
        "Cr": 18.1,
        "Ni": 8.2,
        "Mn": 1.5,
        "Si": 0.5,
        "Fe": "Bal.",
    }

    # Initial prediction: Cr/Ni = 18.1 / 8.2 = 2.21.
    # Should be identified as F4.
    res_before = client.post("/api/analyze", json={"composition": comp})
    assert res_before.status_code == 200
    assert res_before.get_json()["familyCode"] == "F4"

    # 2. Inject an impossible gate for F4 in SQLite: Cr / Ni must be [0.1, 0.5]
    # (Since actual Cr/Ni is 2.21, this gate will block F4)
    restrictive_gate = [
        {
            "id": "gate-test-block",
            "name": "Cr / Ni",
            "numerator": "Cr",
            "denominator": "Ni",
            "min": 0.1,
            "max": 0.5,
            "rationale": "Test gate designed to block 18/8 SS",
            "enabled": True,
        }
    ]
    put_res = client.put("/api/gates/F4", json={"gates": restrictive_gate})
    assert put_res.status_code == 200

    try:
        # 3. Re-run analysis: F4 must now be blocked because Cr/Ni (2.25) is outside [0.1, 0.5]
        res_after = client.post("/api/analyze", json={"composition": comp})
        assert res_after.status_code == 200
        after_data = res_after.get_json()

        # F4 should either not be the top family, or the checks should show the ratio gate blocked
        top_family = after_data.get("familyCode")
        f4_checks = [c for c in after_data.get("checks", []) if c.get("element") == "Cr / Ni"]
        # If F4 remained top (e.g. if no other family fits at all), it must be contradicted or flagged
        if top_family == "F4":
            assert any(not c.get("passed") for c in f4_checks) or after_data["decision"] != "identified"
        else:
            # F4 was successfully excluded by the custom gate
            assert top_family != "F4"
    finally:
        # Clean up: restore reasonable default gate for F4 so other tests aren't affected
        default_gate = [
            {
                "id": "gate-test-restore",
                "name": "Cr / Ni",
                "numerator": "Cr",
                "denominator": "Ni",
                "min": 1.4,
                "max": 3.2,
                "rationale": "Standard F4 ratio gate",
                "enabled": True,
            }
        ]
        client.put("/api/gates/F4", json={"gates": default_gate})


def test_real_gate_validation_endpoint(client):
    """
    Audit fix #5.13: POST /api/gates/validate tests current gates against
    real reference spectrum centroids from materials.json.
    """
    payload = {
        "family_code": "F4",
        "gates": [
            {
                "name": "Cr / Ni",
                "numerator": "Cr",
                "denominator": "Ni",
                "min": 1.8,
                "max": 2.6,
                "enabled": True,
            }
        ],
    }
    res = client.post("/api/gates/validate", json=payload)
    assert res.status_code == 200
    metrics = res.get_json()
    assert "total" in metrics
    assert "passing" in metrics
    assert "failing" in metrics
    assert metrics["passing"] + metrics["failing"] == metrics["total"]
    assert "centroids" in metrics.get("note", "").lower() or "materials.json" in metrics.get("note", "").lower()
