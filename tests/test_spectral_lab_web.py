"""
tests/test_spectral_lab_web.py
==============================
Automated tests for Spectral Lab Flask web server and rule-based microanalysis API.
Tests cover:
  - System health and knowledge base integrity
  - Full family catalog retrieval (12 metallurgical families)
  - Manual microanalysis prediction (Austenitic SS 304, Bronze, Carbon steel)
  - Safe abstention on sparse input ({S: 0.2} -> UNKNOWN)
  - Real PDF report ingest and spectral table extraction
  - Ratio gate updates, SQLite persistence, and validation metrics
  - Audit log and user management CRUD operations
  - Frontend SPA static serving
"""

import io
import json
import os
import sys
from pathlib import Path

import pytest

# Add repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from server import app, get_db_connection


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["knowledge_base_loaded"] is True
    assert data["families_count"] == 12
    assert data["rule_engine"] == "deterministic_compatibility_scoring"


def test_list_families(client):
    res = client.get("/api/families")
    assert res.status_code == 200
    families = res.get_json()
    assert isinstance(families, list)
    assert len(families) == 12

    codes = [f["code"] for f in families]
    assert "F4" in codes   # Austenitic stainless steel 18/8
    assert "F1a" in codes  # Plain / low-Mn carbon steel
    assert "F1b" in codes  # ~1.5 Mn plain carbon steel
    assert "F6a" in codes  # Cu-Sn bronze
    assert "F7" in codes   # Au-plated electrical contact

    # Check F4 structure
    f4 = next(f for f in families if f["code"] == "F4")
    assert "Austenitic" in f4["name"]
    assert len(f4["elementBands"]) > 0
    assert len(f4["ratioGates"]) > 0
    assert len(f4["candidateComponents"]) > 0


def test_get_family_detail(client):
    res = client.get("/api/families/F4")
    assert res.status_code == 200
    data = res.get_json()
    assert data["code"] == "F4"
    assert data["name"] == "Austenitic stainless steel 18/8"

    res_missing = client.get("/api/families/NON_EXISTENT")
    assert res_missing.status_code == 404


def test_analyze_austenitic_stainless_steel(client):
    """
    Test standard austenitic 18/8 composition.
    Cr=18.1, Ni=8.2, Mn=1.5, Si=0.5 -> Fe Balance.
    Should be identified as F4 Austenitic stainless steel 18/8 with high compatibility.
    """
    payload = {
        "composition": {
            "Cr": 18.1,
            "Ni": 8.2,
            "Mn": 1.5,
            "Si": 0.5,
            "Fe": "Bal.",
        }
    }
    res = client.post("/api/analyze", json=payload)
    assert res.status_code == 200
    data = res.get_json()

    assert data["decision"] == "identified"
    assert data["familyCode"] == "F4"
    assert "Austenitic stainless steel" in data["materialFamily"]
    assert data["compatibilityPct"] >= 80

    candidates = [c["name"] for c in data["candidateComponents"]]
    assert "Magnet housing" in candidates or "Back Flow Tube" in candidates or "Locking Sleeve" in candidates


def test_analyze_sparse_input_abstains(client):
    """
    Sparse input {S: 0.2} must NOT return a false confident match (e.g. Guide Bush).
    The deterministic compatibility engine must safely abstain (UNKNOWN).
    """
    payload = {
        "composition": {
            "S": 0.2
        }
    }
    res = client.post("/api/analyze", json=payload)
    assert res.status_code == 200
    data = res.get_json()

    assert data["decision"] == "unknown"
    assert data["materialFamily"] == "Unclassified Material"
    assert data["compatibilityPct"] == 0
    assert len(data["candidateComponents"]) == 0


def test_analyze_bronze_alloy(client):
    """
    Bronze particle composition with high Cu, Sn matrix.
    Should match F6a Cu-Sn bronze.
    """
    payload = {
        "composition": {
            "Cu": 88.5,
            "Sn": 10.5,
            "P": 0.4,
            "Fe": 0.3,
        }
    }
    res = client.post("/api/analyze", json=payload)
    assert res.status_code == 200
    data = res.get_json()

    assert data["decision"] in ("identified", "ambiguous")
    assert data["familyCode"] in ("F6a", "F6b")


def test_analyze_pdf_upload(client):
    """
    Upload real EDS analysis report PDF:
    Field CRI.I. 26-108 Particle In IC Stud (ISUZU) ......14.pdf
    Should extract EDS table and identify plain carbon steel.
    """
    pdf_path = REPO_ROOT / "Field CRI.I. 26-108 Particle In IC Stud (ISUZU) ......14.pdf"
    if not pdf_path.exists():
        pytest.skip("Sample PDF file not found")

    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    data = {
        "file": (io.BytesIO(file_bytes), "Field_26-108.pdf")
    }
    res = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    result = res.get_json()

    assert result["decision"] == "identified"
    assert "carbon steel" in result["materialFamily"].lower()
    assert "CRI Injector Body" in [c["name"] for c in result["candidateComponents"]] or \
           "IC Stud" in [c["name"] for c in result["candidateComponents"]]
    assert "Fe" in result["extractedComposition"]


def test_ratio_gates_crud_and_validation(client):
    """Test getting, updating, and validating ratio gates."""
    # 1. Get gates for F4
    res = client.get("/api/gates?family_id=F4")
    assert res.status_code == 200
    data = res.get_json()
    assert data["family_id"] == "F4"
    assert len(data["gates"]) > 0

    # 2. Update gates
    updated_gates = [
        {
            "id": "gate-test-1",
            "name": "Cr / Ni",
            "numerator": "Cr",
            "denominator": "Ni",
            "min": 1.80,
            "max": 2.25,
            "rationale": "Custom lab test gate",
            "enabled": True,
        }
    ]
    put_res = client.put("/api/gates/F4", json={"gates": updated_gates})
    assert put_res.status_code == 200

    # Verify updated in get
    res_after = client.get("/api/gates?family_id=F4")
    assert res_after.status_code == 200
    gates_after = res_after.get_json()["gates"]
    assert len(gates_after) == 1
    assert gates_after[0]["name"] == "Cr / Ni"
    assert gates_after[0]["min"] == 1.80

    # 3. Validate preview
    val_res = client.post("/api/gates/validate", json={"family_code": "F4", "gates": updated_gates})
    assert val_res.status_code == 200
    metrics = val_res.get_json()
    assert metrics["total"] > 0
    assert metrics["passing"] + metrics["failing"] == metrics["total"]


def test_audit_logs_endpoint(client):
    """Test retrieving and adding audit logs."""
    res = client.get("/api/audit-logs")
    assert res.status_code == 200
    logs = res.get_json()
    assert isinstance(logs, list)
    initial_count = len(logs)

    new_log = {
        "user": "Dr. Arthur Thorne",
        "userRole": "Snr. Metallurgist",
        "action": "Calibration test run",
        "actionType": "Calibration",
        "familyCode": "F4",
        "changeDetails": {"from": "A", "to": "B"},
        "impactText": "Test audit entry",
        "impactType": "positive",
    }
    post_res = client.post("/api/audit-logs", json=new_log)
    assert post_res.status_code == 200

    res2 = client.get("/api/audit-logs")
    logs2 = res2.get_json()
    assert len(logs2) == initial_count + 1
    assert any(l["action"] == "Calibration test run" for l in logs2)


def test_users_endpoint(client):
    """Test retrieving, adding, and updating users."""
    res = client.get("/api/users")
    assert res.status_code == 200
    users = res.get_json()
    assert len(users) >= 5

    # Add user
    new_user = {
        "id": "user-test-99",
        "name": "Elena Vance",
        "email": "e.vance@spectrallab.io",
        "role": "Lab Tech",
        "department": "Operations",
        "permissions": "Read-only",
    }
    post_res = client.post("/api/users", json=new_user)
    assert post_res.status_code == 200

    # Update user
    put_res = client.put("/api/users/user-test-99", json={"isActive": False, "role": "Auditor"})
    assert put_res.status_code == 200

    res_after = client.get("/api/users")
    user_updated = next(u for u in res_after.get_json() if u["id"] == "user-test-99")
    assert user_updated["isActive"] is False
    assert user_updated["role"] == "Auditor"


def test_spa_serving(client):
    """Test serving the built React frontend."""
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.content_type
