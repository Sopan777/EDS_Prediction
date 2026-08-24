"""
compare_models.py
==================
Run EVERY trained model against the same spectrum/spectra and print their
predictions side by side - so you can see where models agree, where they
disagree, and how confident each one is.

Two input modes:
  1. A report file (PDF/DOCX) - runs eds_extractor first, then compares all
     models on every spectrum found (handles multiple spectra automatically).
  2. A JSON file of hand-built spectra: a list of {element: value} dicts,
     e.g. [{"Fe": 76.0, "Cr": 12.5, ...}, {...}], for comparing models on
     specific test cases without needing a report.

Noise can be toggled the same way as eds_pipeline.py, applied identically
to every model so the comparison stays apples-to-apples.

Usage:
    python compare_models.py report.pdf
    python compare_models.py report.pdf --noise --noise-level 0.25
    python compare_models.py spectra.json --top-k 5
    python compare_models.py report.pdf --save-json outputs/comparison.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

import config
import predictor
from model_registry import all_model_keys
from docx_to_pdf import convert_file, _pick_method, DOC_EXTENSIONS
from eds_extractor import extract_eds_tables

PDF_EXTENSION = ".pdf"


def load_spectra_from_report(input_path: Path) -> List[dict]:
    """Extract every spectrum's element values from a PDF/DOCX report.
    Returns a list of {"label": str, "values": {element: value}} dicts,
    one per spectrum across all tables found."""
    suffix = input_path.suffix.lower()
    if suffix == PDF_EXTENSION:
        pdf_path = input_path
    elif suffix in DOC_EXTENSIONS:
        pdf_path = convert_file(input_path, input_path.parent, _pick_method("auto"))
    else:
        raise ValueError(f"Unsupported file type '{suffix}'.")

    extraction = extract_eds_tables(str(pdf_path))
    spectra = []
    for table in extraction.get("eds_tables", []):
        table_name = table.get("table_name", "")
        for s in table.get("spectra", []):
            spectra.append({
                "label": f"{table_name} / Spectrum {s['spectrum']}",
                "values": s["values"],
            })
    return spectra


def load_spectra_from_json(input_path: Path) -> List[dict]:
    """Load hand-built spectra from a JSON file: either a flat list of
    {element: value} dicts, or a list of {"label": ..., "values": {...}}."""
    with open(input_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    spectra = []
    for i, item in enumerate(raw, start=1):
        if "values" in item:
            spectra.append({"label": item.get("label", f"Sample {i}"), "values": item["values"]})
        else:
            spectra.append({"label": f"Sample {i}", "values": item})
    return spectra


def compare_all_models(
    spectra: List[dict],
    top_k: int = config.DEFAULT_TOP_K,
    confidence_threshold: float = config.CONFIDENCE_THRESHOLD,
    noise_enabled: bool = config.NOISE_ENABLED_DEFAULT,
    noise_level: float = config.NOISE_LEVEL_DEFAULT,
    model_keys: List[str] = None,
) -> List[dict]:
    """
    For every spectrum, run every model and collect their predictions.
    Returns a list (one entry per spectrum) of:
        {
            "label": str,
            "models": {
                "Random Forest": {"top_k": [...], "flag": str|None},
                "CatBoost": {...},
                ...
            }
        }
    Same noise draw is NOT shared across models on purpose - each model call
    re-derives noise from the same random_state per spectrum, so the
    comparison uses the same noisy input for every model on a given spectrum.
    """
    model_keys = model_keys or all_model_keys()
    results = []

    for spec_idx, spectrum in enumerate(spectra):
        entry = {"label": spectrum["label"], "models": {}}
        for model_key in model_keys:
            preds_df = predictor.predict_component(
                spectrum["values"],
                model_key=model_key,
                top_k=top_k,
                confidence_threshold=confidence_threshold,
                noise_enabled=noise_enabled,
                noise_level=noise_level,
                # Same seed per spectrum (not per model) -> every model sees
                # the identical noisy version of this spectrum.
                noise_random_state=config.RANDOM_STATE + spec_idx,
            )
            entry["models"][preds_df.attrs["model_display_name"]] = {
                "top_k": [
                    {"component": row.Component, "probability": float(row.Probability)}
                    for row in preds_df.itertuples()
                ],
                "flag": preds_df.attrs.get("flag"),
            }
        results.append(entry)

    return results


def fmt_pct(p: float) -> str:
    return f"{p * 100:.1f}%"


def print_comparison(results: List[dict], noise_enabled: bool, noise_level: float):
    print(f"Noise: {'ON (' + str(noise_level) + ')' if noise_enabled else 'OFF'}\n")

    for entry in results:
        print("=" * 88)
        print(f"Spectrum: {entry['label']}")
        print("=" * 88)

        model_names = list(entry["models"].keys())
        col_w = max(len(n) for n in model_names) + 2

        # Print each model's top prediction first for a quick scan, then
        # the full top-k underneath.
        print(f"{'Model':<{col_w}} {'Top prediction':<30} {'Confidence':<12} Flag")
        print("-" * 88)
        for name in model_names:
            data = entry["models"][name]
            top = data["top_k"][0] if data["top_k"] else None
            top_label = top["component"] if top else "-"
            top_conf = fmt_pct(top["probability"]) if top else "-"
            flag = "⚠️  LOW CONF" if data.get("flag") else ""
            print(f"{name:<{col_w}} {top_label:<30} {top_conf:<12} {flag}")

        agreement = len({entry["models"][n]["top_k"][0]["component"] for n in model_names
                          if entry["models"][n]["top_k"]})
        if agreement == 1:
            print("\n✅ All models agree on the top prediction.")
        else:
            print(f"\n⚠️  Models DISAGREE — {agreement} different top predictions across "
                  f"{len(model_names)} models.")

        print("\nFull top-k per model:")
        for name in model_names:
            data = entry["models"][name]
            ranked = ", ".join(f"{p['component']} ({fmt_pct(p['probability'])})" for p in data["top_k"])
            print(f"  {name}: {ranked}")
        print()


def save_json(results: list, out_path: str):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Saved comparison to {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Compare every trained EDS component-prediction model on the same spectrum/spectra."
    )
    parser.add_argument("input", help="A PDF/DOCX report, or a JSON file of spectra.")
    parser.add_argument("--models", nargs="*", default=None, choices=list(config.MODEL_REGISTRY.keys()),
                         help="Subset of models to compare (default: all).")
    noise_group = parser.add_mutually_exclusive_group()
    noise_group.add_argument("--noise", dest="noise", action="store_true",
                              help="Inject simulated measurement noise before predicting.")
    noise_group.add_argument("--no-noise", dest="noise", action="store_false")
    parser.set_defaults(noise=config.NOISE_ENABLED_DEFAULT)
    parser.add_argument("--noise-level", type=float, default=config.NOISE_LEVEL_DEFAULT)
    parser.add_argument("--top-k", type=int, default=config.DEFAULT_TOP_K)
    parser.add_argument("--confidence-threshold", type=float, default=config.CONFIDENCE_THRESHOLD)
    parser.add_argument("--save-json", default=None)
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_path}")

    if input_path.suffix.lower() == ".json":
        spectra = load_spectra_from_json(input_path)
    else:
        spectra = load_spectra_from_report(input_path)

    if not spectra:
        print("No spectra found to compare.")
        return

    results = compare_all_models(
        spectra,
        top_k=args.top_k,
        confidence_threshold=args.confidence_threshold,
        noise_enabled=args.noise,
        noise_level=args.noise_level,
        model_keys=args.models,
    )
    print_comparison(results, args.noise, args.noise_level)

    if args.save_json:
        save_json(results, args.save_json)


if __name__ == "__main__":
    main()
