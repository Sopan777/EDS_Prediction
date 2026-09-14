"""
End-to-end tests for the Spectral-Lab MaterialID backend.

Run from the project root:
    pytest tests/test_backend_e2e.py -v

Covers requirement 10 ("Test the complete flow with the existing sample EDS
PDFs..."): PDF upload -> extraction -> Rule-Based Engine -> prediction, plus
the Knowledge Base CRUD/validation loop and audit logging.
"""

import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.paths import SAMPLES_DIR

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "ML" not in body["engine"] or "no ML" in body["engine"]
    assert body["familyCount"] > 0


def test_knowledge_base_loaded_from_materials_json():
    r = client.get("/api/knowledge-base")
    assert r.status_code == 200
    body = r.json()
    assert body["version"]
    assert len(body["families"]) > 0
    fam = body["families"][0]
    assert "elementBands" in fam and "candidateComponents" in fam


@pytest.mark.parametrize("sample_pdf", sorted(p.name for p in SAMPLES_DIR.glob("*.pdf")))
def test_sample_pdf_end_to_end(sample_pdf):
    """PDF -> extraction -> normalization -> Rule-Based Engine, for every bundled sample."""
    r = client.post(f"/api/samples/{quote(sample_pdf)}/analyze")
    assert r.status_code == 200
    body = r.json()
    assert body["tables"], f"no EDS tables extracted from {sample_pdf}"
    for table in body["tables"]:
        result = table["pooledResult"]
        assert result["decision"] in ("identified", "ambiguous", "unknown")
        assert result["scoreLabel"] == "Rule-Based Score"
        assert "ml" not in result["engine"].lower() or "no ml" in result["engine"].lower()
        if result["decision"] == "unknown":
            assert result["candidateComponents"] == []
        else:
            assert result["materialFamily"]


def test_manual_analysis_identifies_known_composition():
    r = client.post("/api/analyze/manual", json={"elements": {"Au": 95.3, "Cu": 2.1, "Ni": 1.9}})
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] == "identified"
    assert body["ruleBasedScore"] > 0
    assert len(body["extractedElements"]) == 3


def test_manual_analysis_rejects_empty_payload():
    r = client.post("/api/analyze/manual", json={"elements": {}})
    assert r.status_code == 400


def test_knowledge_base_crud_round_trip_and_engine_reload():
    payload = {
        "code": "PYTESTFAM",
        "name": "Pytest Alloy",
        "gradeHint": "PT-1",
        "status": "PROV",
        "description": "created by automated test",
        "totalSpectra": 2,
        "elementBands": [{"element": "Pd", "role": "Required", "rangeMin": 80, "rangeMax": 99, "spectraSupport": 2}],
        "ratioGates": [],
        "candidateComponents": [{"name": "Pytest Widget"}],
    }
    before = len(client.get("/api/knowledge-base").json()["families"])

    r = client.post("/api/knowledge-base/families", json=payload)
    assert r.status_code == 200
    assert len(r.json()["families"]) == before + 1

    # the rule engine must see the new family immediately, no restart needed
    r = client.post("/api/analyze/manual", json={"elements": {"Pd": 90.0}})
    assert r.status_code == 200
    assert r.json()["materialFamily"] == "Pytest Alloy"

    payload["description"] = "updated by automated test"
    r = client.put("/api/knowledge-base/families/PYTESTFAM", json=payload)
    assert r.status_code == 200

    r = client.delete("/api/knowledge-base/families/PYTESTFAM")
    assert r.status_code == 200
    assert len(r.json()["families"]) == before


def test_knowledge_base_rejects_invalid_family():
    # negative range should fail validate_knowledge_base's structural checks
    bad_payload = {
        "code": "BADFAM",
        "name": "Bad",
        "gradeHint": "",
        "status": "PROV",
        "description": "",
        "totalSpectra": 1,
        "elementBands": [{"element": "Xx", "role": "Required", "rangeMin": 50, "rangeMax": 10, "spectraSupport": 1}],
        "ratioGates": [],
        "candidateComponents": [],
    }
    r = client.post("/api/knowledge-base/families", json=bad_payload)
    assert r.status_code == 422
    # must not have been persisted
    codes = [f["code"] for f in client.get("/api/knowledge-base").json()["families"]]
    assert "BADFAM" not in codes


def test_audit_log_records_activity():
    before = len(client.get("/api/audit-log").json()["entries"])
    client.post("/api/analyze/manual", json={"elements": {"Fe": 98.0}})
    after = len(client.get("/api/audit-log").json()["entries"])
    assert after == before + 1
