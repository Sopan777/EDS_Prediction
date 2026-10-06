"""
tests/test_isp_engine.py
========================
Comprehensive test suite for the Reference-First Internal Source Prediction (ISP)
v2 architecture (Phases 1-9).
"""

import json
import os
from pathlib import Path
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.test import Client

from isp.decode import decode_row
from isp.registry import (
    INTERNAL_COMPONENTS,
    INDISTINGUISHABILITY_GROUPS,
    parse_candidate_list,
    map_chemistry_to_family,
    normalize_coating,
    map_location_zone,
)
from isp.aggregation import aggregate_site_spectra
from isp.rules import evaluate_domain_family, evaluate_component_domain_rules
from isp.runtime import get_isp_engine, load_trusted_store, predict_internal_source_dict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestPhase1SpectrumDecoderAndRegistry:
    """Tests for Phase 1: Z-Order Spectrum Decoder, Three-State Missingness & Registry."""

    def test_z_order_shift_recovery_exact(self):
        """Verify that an 'In stats.' shifted spectrum recovers true element symbols and 100.00% total."""
        # True elements in Z order: C(6)=8.40, O(8)=2.10, Si(14)=0.45, Cr(24)=9.00, Fe(26)=80.05, Total=100.00
        # Extractor zipped ['In', 'C', 'O', 'Si', 'Cr', 'Fe'] with [8.40, 2.10, 0.45, 9.00, 80.05, 100.00]
        shifted_row = {
            "In": 8.40,
            "C": 2.10,
            "O": 0.45,
            "Si": 9.00,
            "Cr": 80.05,
            "Fe": 100.00,
            "Ni": None,
        }
        decoded = decode_row(shifted_row)
        assert decoded.status == "IN_STATS_Z_SHIFT_RECOVERED"
        assert abs((decoded.total or 0.0) - 100.0) < 1e-6
        assert abs(decoded.sum_wt - 100.0) < 1e-6
        assert decoded.elements["C"] == pytest.approx(8.40)
        assert decoded.elements["O"] == pytest.approx(2.10)
        assert decoded.elements["Si"] == pytest.approx(0.45)
        assert decoded.elements["Cr"] == pytest.approx(9.00)
        assert decoded.elements["Fe"] == pytest.approx(80.05)
        # Three-state missingness: Ni and In must be NOT_REPORTED, never converted to 0.0
        assert decoded.element_states["Ni"] == "NOT_REPORTED"
        assert "Ni" not in decoded.elements
        assert decoded.element_states["In"] == "NOT_REPORTED"
        assert "In" not in decoded.elements

    def test_corrupt_spectrum_quarantined(self):
        """Verify that corrupt spectra with sum >> 100% (like Row 459 Spec 2 & 3) are marked CORRUPT."""
        corrupt_row = {
            "C": 60.0,
            "O": 40.0,
            "Fe": 54.0,
            "Si": 50.0,
        }
        decoded = decode_row(corrupt_row)
        assert decoded.status == "CORRUPT"
        assert decoded.quality_score == 0.0

    def test_controlled_registry_and_external_filtering(self):
        """Verify 35 canonical internal components and strict filtering of external/noise tokens."""
        assert len(INTERNAL_COMPONENTS) == 35
        assert len(INDISTINGUISHABILITY_GROUPS) == 7

        # Multi-source string with internal + external tokens
        internal_ids, records, scope = parse_candidate_list(
            "CRI Injector Body, Valve Piece, Calibration oil tank, Assembly Jig, Tissue Paper"
        )
        assert scope == "MIXED"
        assert "INJECTOR_BODY" in internal_ids
        assert "VALVE_PIECE" in internal_ids
        assert len(internal_ids) == 2
        external_records = [r for r in records if r["cls"] == "EXTERNAL"]
        assert len(external_records) == 3

    def test_location_candidate_name_leakage_guard(self):
        """Verify that location strings naming a specific component are flagged for leakage."""
        zone, leak = map_location_zone("Particle found on Valve Piece", ["VALVE_PIECE"])
        assert leak is True
        assert zone == "BODY_Z_HOLE_VALVE"

        zone_clean, leak_clean = map_location_zone("Filter Edge", ["VALVE_PIECE"])
        assert leak_clean is False
        assert zone_clean == "FILTER_BFT"


class TestPhase2And3AggregationAndRules:
    """Tests for Phase 2 Site Aggregation and Phase 3 Three-Tier Rule Engine."""

    def test_multi_spectrum_site_aggregation_and_heterogeneity(self):
        """Verify site-level median, MAD, min, max, and diagnostic ratios across multiple spectra."""
        s1 = decode_row({"Fe": 97.5, "Cr": 1.5, "Mn": 0.6, "Si": 0.4})
        s2 = decode_row({"Fe": 97.4, "Cr": 1.6, "Mn": 0.6, "Si": 0.4})
        agg = aggregate_site_spectra("SITE_1", "REP_1", [s1, s2])
        assert agg.n_valid_spectra == 2
        assert "HETEROGENEOUS_SPECTRA" not in agg.flags
        assert agg.metal_basis["Fe"] == pytest.approx(97.45, rel=1e-2)
        assert "Cr/Fe" in agg.ratios

    def test_domain_rules_and_coating_decoupling(self):
        """Verify Category A (Domain) evaluation and ZnP surface coating decoupling on bulk steel."""
        # Spectrum on a ZnP-coated plain carbon steel part (Zn=18%, P=7%, Fe=74.3%, Mn=0.7%)
        s_znp = decode_row({"Fe": 74.3, "Zn": 18.0, "P": 7.0, "Mn": 0.7})
        agg = aggregate_site_spectra("SITE_ZNP", "REP_ZNP", [s_znp])
        c_state, c_type, _ = normalize_coating("ZnP Coating")
        assert c_state == "COATED"
        assert c_type == "ZnP"

        # Without ZnP coating decoupling, Zn=18% would contradict Plain Carbon Steel; with decoupling it supports!
        dom_ev = evaluate_domain_family(agg, "PLAIN_C_STEEL", c_state, c_type)
        assert dom_ev.outcome == "SUPPORT"
        assert any("Zn (explained by surface coating)" in el for el in dom_ev.supporting_elements)

        # Component domain rules for IC Stud vs Magnet Core under ZnP coating
        ic_evs = evaluate_component_domain_rules(agg, "IC_STUD", "PLAIN_C_STEEL", "PLAIN_C_STEEL", c_state, c_type)
        mc_evs = evaluate_component_domain_rules(agg, "MAGNET_CORE", "PLAIN_C_STEEL", "PLAIN_C_STEEL", c_state, c_type)
        assert any(e.outcome == "SUPPORT" and "COAT" in e.rule_id for e in ic_evs)
        assert any(e.outcome == "CONTRADICT" and "COAT" in e.rule_id for e in mc_evs)


class TestPhase4To7ReconciliationAndValidationOutputs:
    """Tests verifying Phase 4 Reconciliation and Phase 7 Grouped Cross-Validation outputs."""

    def test_secondary_verification_and_reconciliation_files_exist(self):
        out_dir = PROJECT_ROOT / "data_prep" / "out"
        assert (out_dir / "secondary_verification_log.csv").exists()
        assert (out_dir / "conflict_log.csv").exists()
        assert (out_dir / "data_reconciliation_report.csv").exists()
        assert (out_dir / "validation_report.json").exists()

        with open(out_dir / "validation_report.json", "r", encoding="utf-8") as f:
            val_report = json.load(f)

        # Zero report-level leakage across folds
        assert val_report["report_level_split_leakage"] == 0
        # High candidate set coverage and selective precision
        assert val_report["candidate_set_coverage"] >= 0.90
        assert val_report["high_confidence_selective_precision"] >= 0.90

        # Secondary verification summary checks in trusted store
        store = load_trusted_store()
        sec_summary = store["secondary_verification_summary"]
        assert sec_summary["total_secondary_spectra"] == 176
        assert sec_summary["accepted_level2"] == 4
        assert sec_summary["review_pending"] == 107
        assert sec_summary["rejected_conflicting"] == 25
        assert sec_summary["excluded_no_counterpart"] == 40


class TestPhase8RuntimeAndDjangoEndpoints:
    """Tests for Phase 8 Runtime Engine and Django API endpoints."""

    def test_runtime_engine_predictions_across_3_states(self):
        # 1. Single-component HIGH_CONFIDENCE (Soft Magnetic Pure Iron -> Magnet Core)
        pred_mc = predict_internal_source_dict(
            spectra_inputs=[{"Fe": 99.4, "Mn": 0.2, "Si": 0.2, "C": 0.2}],
            chemistry_raw="Iron Base",
            surface_coating_raw="Nil",
            location_raw="Magnet Group",
        )
        assert pred_mc["prediction_status"] == "HIGH_CONFIDENCE"
        assert pred_mc["predicted_component_id"] == "MAGNET_CORE"

        # 2. AMBIGUOUS with Indistinguishability Group (HSS W-Mo-V spectrum -> Nozzle Needle / Control Piston)
        pred_hss = predict_internal_source_dict(
            spectra_inputs=[{"Fe": 82.7, "W": 6.2, "Mo": 5.0, "Cr": 4.1, "V": 2.0}],
            chemistry_raw="HSS",
            surface_coating_raw="Nil",
            location_raw="Filter",
        )
        assert pred_hss["prediction_status"] == "AMBIGUOUS"
        assert pred_hss["indistinguishability_group"] is not None
        assert pred_hss["indistinguishability_group"]["group_id"] == "HSS_NEEDLE_PISTON_GROUP"

        # 3. UNKNOWN on external organic/salt contaminant (C + O + Na + Cl + Ca, zero structural metals)
        pred_ext = predict_internal_source_dict(
            spectra_inputs=[{"C": 62.0, "O": 31.0, "Na": 3.5, "Cl": 2.5, "Ca": 1.0}],
            chemistry_raw="Carbon Base",
            surface_coating_raw="Nil",
            location_raw="Filter",
        )
        assert pred_ext["prediction_status"] == "UNKNOWN"

    def test_django_v2_predict_and_reconciliation_endpoints(self):
        client = Client()

        # Test /api/v2/predict
        resp = client.post(
            "/api/v2/predict",
            data=json.dumps({
                "spectra": [{"Fe": 99.4, "Mn": 0.2, "Si": 0.2, "C": 0.2}],
                "chemistry": "Iron Base",
                "surface_coating": "Nil",
                "location": "Magnet Group",
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["prediction_status"] == "HIGH_CONFIDENCE"
        assert body["predicted_component_id"] == "MAGNET_CORE"
        assert "candidates" in body
        assert "material_family" in body

        # Test /api/v2/reconciliation
        resp_rec = client.get("/api/v2/reconciliation")
        assert resp_rec.status_code == 200
        rec_body = resp_rec.json()
        assert len(rec_body["reconciliation_table"]) == 46  # 35 internal + 11 excluded secondary-only
        assert "validation_metrics" in rec_body
        assert "secondary_verification_summary" in rec_body

        # Test backward-compatible /api/analyze includes internal_source_prediction
        resp_v1 = client.post(
            "/api/analyze",
            data=json.dumps({
                "composition": {"Fe": 82.7, "W": 6.2, "Mo": 5.0, "Cr": 4.1, "V": 2.0},
                "chemistry": "HSS",
                "surface_coating": "Nil",
                "location": "Filter",
            }),
            content_type="application/json",
        )
        assert resp_v1.status_code == 200
        v1_body = resp_v1.json()
        assert "internal_source_prediction" in v1_body
        assert v1_body["internal_source_prediction"]["prediction_status"] == "AMBIGUOUS"

    def test_analyzer_single_card_ui_and_excel_template_workflow(self):
        """Verify single 'Spectral Ingestion & Elemental wt%' section, dataset-driven element list, and Excel template round-trip."""
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile

        client = Client()
        resp = client.get("/analyzer/")
        assert resp.status_code == 200
        html = resp.content.decode("utf-8")

        # 1. Must appear ONLY ONCE (not duplicated)
        assert html.count("Spectral Ingestion & Elemental wt%") == 1
        assert 'id="tab-btn-upload"' in html
        assert 'id="tab-btn-manual"' in html
        assert "Drag and drop EDS file here" in html
        assert "Download Template" in html
        assert "window.DATASET_ELEMENTS =" in html
        # Verify unrelated periodic-table elements are NOT in DATASET_ELEMENTS
        assert '"symbol": "Xe"' not in html
        assert '"symbol": "U"' not in html

        # 2. Download Excel template and round-trip through /api/extract and /api/analyze
        tpl_resp = client.get("/api/template/excel")
        assert tpl_resp.status_code == 200
        xlsx_bytes = tpl_resp.content
        assert len(xlsx_bytes) > 1000

        upload_file = SimpleUploadedFile(
            "Dhatu_Bodh_EDS_Template.xlsx",
            xlsx_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        ext_resp = client.post("/api/extract", {"file": upload_file})
        assert ext_resp.status_code == 200
        ext_data = ext_resp.json()
        assert ext_data["status"] == "extracted"
        assert len(ext_data["spectra"]) == 1
        assert ext_data["spectra"][0]["Fe"] == pytest.approx(97.6)
        assert ext_data["spectra"][0]["Cr"] == pytest.approx(1.5)

