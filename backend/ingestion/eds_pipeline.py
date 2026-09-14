"""
eds_pipeline.py
================
End-to-end pipeline: EDS/EDAX report (PDF or DOCX) -> extracted tables ->
material-family identification for EVERY spectrum table in the report.

    PDF/DOCX
       |  eds_geometry.extract_tables()            (word-geometry; falls back
       |    -> eds_extractor.extract_eds_tables()      to character-offset
       v                                               parsing if PyMuPDF is
    { eds_tables: [ { spectra: [...] }, ... ] }        unavailable)
       |  rule_engine.scoring.predict_particle()   per table (spectra pooled)
       |  rule_engine.scoring.predict_spectrum()   per spectrum (detail)
       v
    family / grade / ranked candidates + caveats, printed / saved as JSON

This previously called predictor.predict_component(), the machine-learning
path. That path cannot run: no trained model artifacts exist anywhere on disk
(saved_models/ is absent), so every call raised FileNotFoundError before a
single prediction was made. It has been replaced with the deterministic
compatibility engine in rule_engine/scoring.py, which is described in
docs/EDS_AUDIT.md and is the only functioning predictor in this project.

Two answers are produced per table, and they read differently on purpose:
  - a POOLED answer, treating every spectrum in the table as repeat
    measurements of one particle (the previous engine's majority-vote
    equivalent, but combining evidence instead of voting on it)
  - a PER-SPECTRUM answer for each row, useful when a table in fact covers
    more than one physical location (see 26-130's "Ball Damage" site, which
    is a different particle from the seat-area sites on the same PDF)

Usage:
    python eds_pipeline.py report.pdf
    python eds_pipeline.py report.docx
    python eds_pipeline.py report.pdf --save-json outputs/report_predictions.json
    python eds_pipeline.py report.pdf --per-spectrum
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional

import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from backend.ingestion.docx_to_pdf import DOC_EXTENSIONS, _pick_method, convert_file
except ImportError:
    from docx_to_pdf import DOC_EXTENSIONS, _pick_method, convert_file

from rule_engine.scoring import Decision, Prediction, predict_particle, predict_spectrum

try:
    from backend.ingestion import eds_geometry
except ImportError:
    try:
        import eds_geometry
    except ImportError:  # pragma: no cover - PyMuPDF genuinely absent
        eds_geometry = None

try:
    from backend.ingestion.eds_extractor import extract_eds_tables as _extract_eds_tables_text
except ImportError:
    from eds_extractor import extract_eds_tables as _extract_eds_tables_text

PDF_EXTENSION = ".pdf"


def resolve_to_pdf(input_path: Path) -> Path:
    """Convert DOCX/DOC to PDF first if necessary; pass PDFs through as-is."""
    suffix = input_path.suffix.lower()
    if suffix == PDF_EXTENSION:
        return input_path
    if suffix in DOC_EXTENSIONS:
        method = _pick_method("auto")
        return convert_file(input_path, input_path.parent, method)
    raise ValueError(
        "Unsupported file type '" + suffix + "'. Please provide a .pdf, .docx, or .doc file."
    )


def extract_tables(pdf_path: str) -> dict:
    """Extract every composition table, preferring word-geometry parsing.

    The character-offset extractor in eds_extractor.py mis-parses these
    reports: narrow columns are separated by a single space rather than the
    2+ spaces it requires, and numeric cells are not aligned to the header's
    character offsets. Confirmed on all three sample reports - the 26-146
    table came back as elements=['O','F'] with every value None against a
    real C/O/F/Cr/Cu/Sn table. eds_geometry.py fixes this by anchoring columns
    to each word's bounding-box centre instead of character position.

    Falls back to the text-based extractor only when PyMuPDF is unavailable,
    so this pipeline still runs (with degraded ingest) rather than failing
    outright on an incomplete environment.
    """
    if eds_geometry is not None and eds_geometry.available():
        result = eds_geometry.extract_tables(pdf_path)
        if result is not None:
            return result
    return _extract_eds_tables_text(pdf_path)


def _clean_values(raw_values: dict) -> dict:
    """Drop the pseudo-element 'Total' and any value the extractor left blank.

    A blank cell means the element was analysed but not reported for that
    spectrum - that is exactly the state normalize_spectrum needs to see as
    "below detection limit" rather than "not analysed", which is why it is
    dropped from the values dict rather than coerced to 0.0: the analysed_
    elements list (the table's column set) still carries the fact that this
    element WAS in the analysed set.
    """
    return {
        element: value
        for element, value in raw_values.items()
        if element != "Total" and value is not None
    }


def _prediction_to_json(prediction: Prediction) -> dict:
    return prediction.to_dict()


def run_pipeline(input_path: str, per_spectrum: bool = False) -> dict:
    """Run extraction + identification end-to-end.

    Returns a JSON-serialisable dict: the extractor's own table structure,
    with a "pooled_prediction" added to every table (all its spectra treated
    as repeat measurements of one particle) and, if requested, a
    "prediction" added to every individual spectrum.
    """
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError("File not found: " + str(path))

    pdf_path = resolve_to_pdf(path)
    extraction = extract_tables(str(pdf_path))

    for table in extraction.get("eds_tables", []):
        columns = [e for e in table.get("elements", []) if e != "Total"]
        spectra = table.get("spectra", [])
        cleaned = [_clean_values(s.get("values", {})) for s in spectra]
        non_empty = [v for v in cleaned if v]

        if non_empty:
            pooled = predict_particle(non_empty, analysed_elements=columns)
        else:
            pooled = Prediction(decision=Decision.UNKNOWN, reason="no measured values in this table")
        table["pooled_prediction"] = _prediction_to_json(pooled)

        if per_spectrum:
            for spectrum, values in zip(spectra, cleaned):
                if values:
                    result = predict_spectrum(values, analysed_elements=columns)
                else:
                    result = Prediction(decision=Decision.UNKNOWN, reason="no measured values")
                spectrum["prediction"] = _prediction_to_json(result)

    extraction["prediction_settings"] = {
        "engine": "rule_engine.scoring (deterministic compatibility scoring)",
        "knowledge_base_version": _knowledge_base_version(),
        "per_spectrum": per_spectrum,
    }
    return extraction


def _knowledge_base_version() -> Optional[str]:
    try:
        from rule_engine.scoring import get_knowledge_base

        return get_knowledge_base().version
    except Exception:
        return None


def print_result(result: dict, per_spectrum: bool = False):
    tables = result.get("eds_tables", [])
    if not tables:
        print(result.get("message", "No EDS table found."))
        return

    settings = result.get("prediction_settings", {})
    print("Engine: " + str(settings.get("engine")))
    kb_version = settings.get("knowledge_base_version")
    if kb_version:
        print("Knowledge base version: " + str(kb_version))

    for t_idx, table in enumerate(tables, start=1):
        print("\nTable " + str(t_idx) + ": " + str(table.get("table_name")) + " (page " + str(table.get("page")) + ")")
        pooled = table.get("pooled_prediction", {})
        _print_prediction(pooled, indent="  ", label="Pooled (" + str(len(table.get("spectra", []))) + " spectra)")

        if per_spectrum:
            for spectrum in table.get("spectra", []):
                pred = spectrum.get("prediction")
                if pred:
                    _print_prediction(pred, indent="    ", label="Spectrum " + str(spectrum.get("spectrum")))


def _print_prediction(pred: dict, indent: str, label: str):
    print(indent + label + ": " + pred.get("decision", "?").upper())
    if pred.get("material_family"):
        print(indent + "  family:        " + pred["material_family"])
        if pred.get("grade_hint"):
            print(indent + "  grade hint:    " + pred["grade_hint"])
        print(
            indent
            + "  compatibility: "
            + str(round(pred.get("compatibility", 0.0), 3))
            + "   margin: "
            + str(round(pred.get("margin", 0.0), 3))
        )
        candidates = pred.get("candidate_components", [])
        if candidates:
            shown = ", ".join(candidates[:6])
            more = " (+" + str(len(candidates) - 6) + " more)" if len(candidates) > 6 else ""
            print(indent + "  candidates:    " + shown + more)
    else:
        print(indent + "  reason: " + str(pred.get("reason", "")))
    for caveat in pred.get("caveats", [])[:2]:
        print(indent + "  caveat: " + caveat)


def save_json(result: dict, out_path: str):
    out_path_obj = Path(out_path)
    out_path_obj.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path_obj, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print("\nSaved results to " + str(out_path_obj))


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Extract EDS spectra from a PDF/DOCX report and identify the "
            "material family for each table (and optionally each spectrum)."
        )
    )
    parser.add_argument("input", help="Path to a PDF or DOCX EDS/EDAX report.")
    parser.add_argument(
        "--per-spectrum",
        action="store_true",
        help="Also report a family for each individual spectrum, not just the pooled table result.",
    )
    parser.add_argument("--save-json", default=None, help="Path to save the full result as JSON.")
    args = parser.parse_args()

    result = run_pipeline(args.input, per_spectrum=args.per_spectrum)
    print_result(result, per_spectrum=args.per_spectrum)

    if args.save_json:
        save_json(result, args.save_json)


if __name__ == "__main__":
    main()
