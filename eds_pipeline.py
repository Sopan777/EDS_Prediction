"""
eds_pipeline.py
================
End-to-end pipeline: EDS/EDAX report (PDF or DOCX) -> extracted tables ->
component prediction for EVERY spectrum in EVERY table.

    PDF/DOCX
       │  eds_extractor.extract_eds_tables()
       ▼
    { eds_tables: [ { spectra: [ {element: value, ...}, ... ] }, ... ] }
       │  predictor.predict_component() per spectrum
       ▼
    predictions attached back onto each spectrum + printed / saved as JSON

Options (all exposed as CLI flags, see --help):
  --model            which trained model to use (random_forest / extra_trees
                      / catboost / xgboost). Defaults to the most
                      noise-robust model chosen during training.
  --noise / --no-noise   on/off toggle for injecting simulated measurement
                      noise into each spectrum before predicting.
  --noise-level       how much noise (relative to training std) when
                      --noise is on.
  --top-k             how many candidate components to return per spectrum.
  --confidence-threshold  below this, flagged "Unknown / needs review".

Usage:
    python eds_pipeline.py report.pdf
    python eds_pipeline.py report.docx --model catboost --noise --noise-level 0.25
    python eds_pipeline.py report.pdf --save-json outputs/report_predictions.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

import config
from docx_to_pdf import convert_file, _pick_method, DOC_EXTENSIONS
from eds_extractor import extract_eds_tables
import predictor

PDF_EXTENSION = ".pdf"


def resolve_to_pdf(input_path: Path) -> Path:
    """Convert DOCX/DOC to PDF first if necessary; pass PDFs through as-is."""
    suffix = input_path.suffix.lower()
    if suffix == PDF_EXTENSION:
        return input_path
    if suffix in DOC_EXTENSIONS:
        method = _pick_method("auto")
        return convert_file(input_path, input_path.parent, method)
    raise ValueError(f"Unsupported file type '{suffix}'. Please provide a .pdf, .docx, or .doc file.")


def fmt_pct(p: float) -> str:
    return f"{p * 100:.1f}%"


def run_pipeline(
    input_path: str,
    model_key: str = None,
    top_k: int = config.DEFAULT_TOP_K,
    confidence_threshold: float = config.CONFIDENCE_THRESHOLD,
    noise_enabled: bool = config.NOISE_ENABLED_DEFAULT,
    noise_level: float = config.NOISE_LEVEL_DEFAULT,
) -> dict:
    """
    Run extraction + prediction end-to-end and return a JSON-serialisable
    dict: the extractor's own table structure, with a "predictions" list
    added onto every spectrum.
    """
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    pdf_path = resolve_to_pdf(path)
    extraction = extract_eds_tables(str(pdf_path))

    model_key = model_key or predictor.default_model_key()

    for table in extraction.get("eds_tables", []):
        for spectrum in table.get("spectra", []):
            preds_df = predictor.predict_component(
                spectrum["values"],
                model_key=model_key,
                top_k=top_k,
                confidence_threshold=confidence_threshold,
                noise_enabled=noise_enabled,
                noise_level=noise_level,
            )
            spectrum["predictions"] = {
                "model": preds_df.attrs.get("model_display_name"),
                "noise_enabled": preds_df.attrs.get("noise_enabled"),
                "noise_level": preds_df.attrs.get("noise_level"),
                "top_k": [
                    {"component": row.Component, "probability": float(row.Probability)}
                    for row in preds_df.itertuples()
                ],
                "flag": preds_df.attrs.get("flag"),
            }

    extraction["prediction_settings"] = {
        "model": predictor.get_model(model_key).display_name,
        "noise_enabled": noise_enabled,
        "noise_level": noise_level if noise_enabled else 0.0,
        "top_k": top_k,
        "confidence_threshold": confidence_threshold,
    }
    return extraction


def print_result(result: dict):
    tables = result.get("eds_tables", [])
    if not tables:
        print(result.get("message", "No EDS table found."))
        return

    settings = result.get("prediction_settings", {})
    print(f"Model: {settings.get('model')}   "
          f"Noise: {'ON (' + str(settings.get('noise_level')) + ')' if settings.get('noise_enabled') else 'OFF'}")

    for t_idx, table in enumerate(tables, start=1):
        print(f"\nTable {t_idx}: {table.get('table_name')} (page {table.get('page')})")
        for spectrum in table.get("spectra", []):
            preds = spectrum.get("predictions", {})
            print(f"  Spectrum {spectrum['spectrum']}:")
            for rank, p in enumerate(preds.get("top_k", []), start=1):
                print(f"    {rank}. {p['component']:<30s} {fmt_pct(p['probability'])}")
            if preds.get("flag"):
                print(f"    ⚠️  {preds['flag']}")


def save_json(result: dict, out_path: str):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nSaved predictions to {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract EDS spectra from a PDF/DOCX report and predict the component for each one."
    )
    parser.add_argument("input", help="Path to a PDF or DOCX EDS/EDAX report.")
    parser.add_argument("--model", default=None,
                         choices=list(config.MODEL_REGISTRY.keys()),
                         help="Model to use for prediction (default: most noise-robust model from training).")
    noise_group = parser.add_mutually_exclusive_group()
    noise_group.add_argument("--noise", dest="noise", action="store_true",
                              help="Inject simulated measurement noise into each spectrum before predicting.")
    noise_group.add_argument("--no-noise", dest="noise", action="store_false",
                              help="Predict on the extracted values as-is (default).")
    parser.set_defaults(noise=config.NOISE_ENABLED_DEFAULT)
    parser.add_argument("--noise-level", type=float, default=config.NOISE_LEVEL_DEFAULT,
                         help="Noise magnitude relative to each element's training std (used only with --noise).")
    parser.add_argument("--top-k", type=int, default=config.DEFAULT_TOP_K)
    parser.add_argument("--confidence-threshold", type=float, default=config.CONFIDENCE_THRESHOLD)
    parser.add_argument("--save-json", default=None, help="Path to save the full result as JSON.")
    args = parser.parse_args()

    result = run_pipeline(
        args.input,
        model_key=args.model,
        top_k=args.top_k,
        confidence_threshold=args.confidence_threshold,
        noise_enabled=args.noise,
        noise_level=args.noise_level,
    )
    print_result(result)

    if args.save_json:
        save_json(result, args.save_json)


if __name__ == "__main__":
    main()
