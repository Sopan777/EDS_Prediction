"""
tests/test_e2e_real_pdf.py
==========================
End-to-end integration test executing real EDS PDF ingestion through
the complete application pipeline:
  PDF upload -> eds_pipeline word-geometry extraction -> predict_particle()
  -> scoring engine -> database persistence (analysis_history, audit_logs, uploaded_files)
  -> API response verification.

Uses the real analyst-labelled EDS report:
  data/reports/Field CRI.I. 26-108 Particle In IC Stud (ISUZU) ......14.pdf
"""

import io
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


def test_e2e_real_pdf_pipeline(client):
    """
    Ingest real report PDF through POST /api/analyze and verify
    extraction, identification, and database persistence.
    """
    pdf_path = (
        REPO_ROOT
        / "data"
        / "reports"
        / "Field CRI.I. 26-108 Particle In IC Stud (ISUZU) ......14.pdf"
    )
    if not pdf_path.exists():
        pdf_path = REPO_ROOT / "Field CRI.I. 26-108 Particle In IC Stud (ISUZU) ......14.pdf"
    if not pdf_path.exists():
        pytest.skip(f"Sample PDF file not found at {pdf_path}")

    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    data = {
        "file": (io.BytesIO(file_bytes), "Field_CRI_26-108.pdf"),
        "session_id": "session-e2e-test",
    }

    res = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert res.status_code == 200, f"Upload failed: {res.get_data(as_text=True)}"
    result = res.get_json()

    # 1. Decision verification
    assert result["decision"] == "identified"
    assert "carbon steel" in result["materialFamily"].lower()
    assert result["familyCode"] in ("F1a", "F1b", "F1c")

    # 2. Composition extracted from report
    extracted = result["extractedComposition"]
    assert "Fe" in extracted, "Expected Fe in extracted composition"
    assert extracted["Fe"] > 50.0, "Expected steel with >50 wt% Fe"

    # 3. Compatibility score must be valid percentage
    assert 0 <= result["compatibilityPct"] <= 100

    # 4. Candidate components must contain IC Stud or CRI Injector Body
    candidate_names = [c["name"] for c in result["candidateComponents"]]
    assert any(
        kw in name for name in candidate_names for kw in ("IC Stud", "CRI Injector Body", "Guide Bush")
    ), f"Expected IC Stud or related candidate, got: {candidate_names}"

    # 5. Database persistence verification
    analysis_id = result["analysisId"]
    assert analysis_id is not None

    conn = get_db_connection()
    cur = conn.cursor()

    # Verify analysis_history row
    cur.execute("SELECT * FROM analysis_history WHERE id = ?", (analysis_id,))
    history_row = cur.fetchone()
    assert history_row is not None, f"Analysis {analysis_id} not found in analysis_history"
    assert history_row["decision"] == "identified"
    assert history_row["session_id"] == "session-e2e-test"

    # Verify uploaded_files row
    cur.execute("SELECT * FROM uploaded_files WHERE analysis_id = ?", (analysis_id,))
    upload_row = cur.fetchone()
    assert upload_row is not None, "File upload not recorded in uploaded_files table"
    assert upload_row["original_filename"] == "Field_CRI_26-108.pdf"

    # Verify audit log entry
    cur.execute("SELECT * FROM audit_logs WHERE action LIKE ? ORDER BY timestamp DESC LIMIT 1", ("%Field_CRI_26-108.pdf%",))
    # Or check recent audit log
    cur.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 1")
    audit_row = cur.fetchone()
    assert audit_row is not None
    assert "Microanalysis" in audit_row["action"]

    conn.close()
