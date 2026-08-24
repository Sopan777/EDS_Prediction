"""
app.py
======
One combined terminal tool for the EDS/EDAX pipeline:

    report (.pdf, .docx, or .doc)
        -> [.docx/.doc: converted to PDF via docx_to_pdf.py]
        -> fed into eds_extractor.py
        -> every spectrum's composition run through predictor.py
        -> EDS composition + per-spectrum component prediction,
           shown in-terminal and saved next to the report

If a table has more than one spectrum, each spectrum gets its own
prediction (not just a single table-wide guess) - plus a table-level
"consensus" prediction rolled up across all of that table's spectra, so
you can see both the per-spot read and the overall call at a glance.

Just run it and follow the prompts:

    python app.py

Or process one file non-interactively and exit:

    python app.py "C:\reports\some_report.docx"

This is a terminal-only tool (no web UI) - it needs `eds_extractor.py`,
`predictor.py`, and `docx_to_pdf.py` in the same folder, since it imports
them directly. It does not modify any of those files.
"""

from __future__ import annotations

import itertools
import json
import sys
import threading
import time
from collections import Counter
from pathlib import Path

try:
    import config
except ImportError:
    print("ERROR: config.py wasn't found. Put app.py in the eds_pipeline folder.")
    sys.exit(1)

try:
    from eds_extractor import extract_eds_tables
except ImportError:
    print("ERROR: eds_extractor.py wasn't found. Put app.py in the same "
          "folder as eds_extractor.py, predictor.py, and docx_to_pdf.py.")
    sys.exit(1)

try:
    import predictor
except ImportError:
    print("ERROR: predictor.py wasn't found. Put app.py in the same "
          "folder as eds_extractor.py, predictor.py, and docx_to_pdf.py.")
    sys.exit(1)

try:
    from docx_to_pdf import convert_file as docx_convert_file, _pick_method
except ImportError:
    print("ERROR: docx_to_pdf.py wasn't found. Put app.py in the same "
          "folder as eds_extractor.py and docx_to_pdf.py.")
    sys.exit(1)


# --------------------------------------------------------------------------
# Colour (optional - falls back to plain text if colorama isn't installed,
# or on a terminal that doesn't support ANSI)
# --------------------------------------------------------------------------

try:
    import colorama
    colorama.init()
    _C = {
        "green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m",
        "cyan": "\033[96m", "bold": "\033[1m", "dim": "\033[2m", "reset": "\033[0m",
    }
except Exception:
    _C = {k: "" for k in ("green", "red", "yellow", "cyan", "bold", "dim", "reset")}


def c(text: str, colour: str) -> str:
    return f"{_C[colour]}{text}{_C['reset']}"


PDF_EXTENSIONS = {".pdf"}
DOC_EXTENSIONS = {".docx", ".doc"}


# --------------------------------------------------------------------------
# Terminal spinner animation
# --------------------------------------------------------------------------

class Spinner:
    """A simple in-place terminal spinner for long-running steps.

    Usage:
        with Spinner("Extracting EDS data"):
            do_the_work()
    """
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str, colour: str = "cyan"):
        self.message = message
        self.colour = colour
        self._stop_event = threading.Event()
        self._thread = None
        self._start_time = None

    def _spin(self):
        for frame in itertools.cycle(self.FRAMES):
            if self._stop_event.is_set():
                break
            elapsed = time.time() - self._start_time
            line = f"\r{c(frame, self.colour)} {self.message}... {c(f'({elapsed:0.1f}s)', 'dim')}   "
            sys.stdout.write(line)
            sys.stdout.flush()
            time.sleep(0.08)

    def __enter__(self):
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        elapsed = time.time() - self._start_time
        # clear the spinner line
        sys.stdout.write("\r" + " " * (len(self.message) + 30) + "\r")
        if exc_type is None:
            print(f"{c('✔', 'green')} {self.message} {c(f'({elapsed:0.1f}s)', 'dim')}")
        else:
            print(f"{c('✘', 'red')} {self.message} {c(f'({elapsed:0.1f}s)', 'dim')}")
        return False  # don't suppress exceptions


# --------------------------------------------------------------------------
# Banner
# --------------------------------------------------------------------------

BANNER = r"""
 ███████╗██████╗ ███████╗    ██████╗ ██╗██████╗ ███████╗██╗     ██╗███╗   ██╗███████╗
 ██╔════╝██╔══██╗██╔════╝    ██╔══██╗██║██╔══██╗██╔════╝██║     ██║████╗  ██║██╔════╝
 █████╗  ██║  ██║███████╗    ██████╔╝██║██████╔╝█████╗  ██║     ██║██╔██╗ ██║█████╗
 ██╔══╝  ██║  ██║╚════██║    ██╔═══╝ ██║██╔═══╝ ██╔══╝  ██║     ██║██║╚██╗██║██╔══╝
 ███████╗██████╔╝███████║    ██║     ██║██║     ███████╗███████╗██║██║ ╚████║███████╗
 ╚══════╝╚═════╝ ╚══════╝    ╚═╝     ╚═╝╚═╝     ╚══════╝╚══════╝╚═╝╚═╝  ╚═══╝╚══════╝
"""


def print_banner():
    print(c(BANNER, "cyan"))
    print(c("  Report in -> EDS/EDAX composition + component prediction out. PDF and DOCX/DOC supported.", "dim"))
    print()


def progress_bar(label: str, duration: float = 0.6, width: int = 28):
    """A quick decorative progress bar for fast steps (file checks etc.)."""
    steps = 18
    for i in range(steps + 1):
        filled = int(width * i / steps)
        bar = "█" * filled + "░" * (width - filled)
        sys.stdout.write(f"\r{label} [{c(bar, 'cyan')}] {int(100*i/steps)}%")
        sys.stdout.flush()
        time.sleep(duration / steps)
    sys.stdout.write("\n")


# --------------------------------------------------------------------------
# Terminal table rendering
# --------------------------------------------------------------------------

def fmt_val(v) -> str:
    if v is None:
        return c("-", "dim")
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def fmt_prediction(pred: dict) -> str:
    """pred: {"top_k": [{"component":..,"probability":..}, ...], "flag": str|None}"""
    if not pred or not pred.get("top_k"):
        return c("-", "dim")
    top = pred["top_k"][0]
    text = f"{top['component']} ({top['probability']*100:.0f}%)"
    if pred.get("flag"):
        text = c(text + "  [low confidence]", "yellow")
    return text


def print_table(headers, rows):
    widths = [len(h) for h in headers]
    str_rows = []
    for row in rows:
        str_row = [str(cell) for cell in row]
        str_rows.append(str_row)
        for i, cell in enumerate(str_row):
            widths[i] = max(widths[i], _visible_len(cell))

    def sep(l, m, r):
        return l + m.join("─" * (w + 2) for w in widths) + r

    def row_line(cells):
        parts = []
        for cell, w in zip(cells, widths):
            pad = w - _visible_len(cell)
            parts.append(" " + cell + " " * (pad + 1))
        return "│" + "│".join(parts) + "│"

    print(sep("┌", "┬", "┐"))
    print(row_line([c(h, "cyan") for h in headers]))
    print(sep("├", "┼", "┤"))
    for str_row in str_rows:
        print(row_line(str_row))
    print(sep("└", "┴", "┘"))


def _visible_len(s: str) -> int:
    plain = s
    for code in _C.values():
        if code:
            plain = plain.replace(code, "")
    return len(plain)


# --------------------------------------------------------------------------
# Prediction enrichment (per spectrum + table-level roll-up)
#
# predictor.py only exposes per-spectrum prediction (predict_component /
# predict_components_batch). When a table has multiple spectra, this adds a
# table-level "consensus" call on top, so the terminal output shows both:
#   - one prediction per spectrum (always - each spot gets its own call)
#   - one rolled-up prediction for the whole table (only meaningful once
#     there's more than one spectrum to roll up)
# --------------------------------------------------------------------------

def _predict_one(values: dict, model_key, top_k, confidence_threshold,
                  noise_enabled, noise_level) -> dict:
    preds_df = predictor.predict_component(
        values,
        model_key=model_key,
        top_k=top_k,
        confidence_threshold=confidence_threshold,
        noise_enabled=noise_enabled,
        noise_level=noise_level,
    )
    return {
        "model": preds_df.attrs.get("model_display_name"),
        "noise_enabled": preds_df.attrs.get("noise_enabled"),
        "noise_level": preds_df.attrs.get("noise_level"),
        "top_k": [
            {"component": row.Component, "probability": float(row.Probability)}
            for row in preds_df.itertuples()
        ],
        "flag": preds_df.attrs.get("flag"),
    }


def _table_level_prediction(spectra: list) -> dict | None:
    """Roll up per-spectrum predictions for a table into one consensus call.

    - Majority vote on each spectrum's #1 component, when spectra disagree.
    - If every spectrum agrees, that's the consensus with 100% agreement.
    Only produced when there's more than one spectrum with a prediction.
    """
    top_choices = [
        s["predicted_component"]["top_k"][0]["component"]
        for s in spectra
        if s.get("predicted_component") and s["predicted_component"].get("top_k")
    ]
    if len(top_choices) < 2:
        return None

    counts = Counter(top_choices)
    winner, win_count = counts.most_common(1)[0]
    agreement = win_count / len(top_choices)

    # average probability the winner got whenever it appeared as top choice
    probs = [
        s["predicted_component"]["top_k"][0]["probability"]
        for s in spectra
        if s.get("predicted_component") and s["predicted_component"].get("top_k")
        and s["predicted_component"]["top_k"][0]["component"] == winner
    ]
    avg_prob = sum(probs) / len(probs) if probs else 0.0

    return {
        "top_k": [{"component": winner, "probability": avg_prob}],
        "method": "majority_vote",
        "agreement": agreement,
        "flag": None,
    }


def enrich_result_with_predictions(
    result: dict,
    model_key: str = None,
    top_k: int = None,
    confidence_threshold: float = None,
    noise_enabled: bool = None,
    noise_level: float = None,
) -> dict:
    """Attach a component prediction to every spectrum in every table, plus
    a table-level consensus prediction when a table has multiple spectra."""
    top_k = top_k if top_k is not None else config.DEFAULT_TOP_K
    confidence_threshold = (confidence_threshold if confidence_threshold is not None
                             else config.CONFIDENCE_THRESHOLD)
    noise_enabled = noise_enabled if noise_enabled is not None else config.NOISE_ENABLED_DEFAULT
    noise_level = noise_level if noise_level is not None else config.NOISE_LEVEL_DEFAULT
    model_key = model_key or predictor.default_model_key()

    for table in result.get("eds_tables", []):
        spectra = table.get("spectra", [])
        for spectrum in spectra:
            spectrum["predicted_component"] = _predict_one(
                spectrum["values"], model_key, top_k, confidence_threshold,
                noise_enabled, noise_level,
            )
        if spectra:
            table["predicted_component"] = _table_level_prediction(spectra)

    result["prediction_settings"] = {
        "model": predictor.get_model(model_key).display_name,
        "noise_enabled": noise_enabled,
        "noise_level": noise_level if noise_enabled else 0.0,
        "top_k": top_k,
        "confidence_threshold": confidence_threshold,
    }
    return result


# --------------------------------------------------------------------------
# Result printing
# --------------------------------------------------------------------------

def print_eds_result(result: dict, source_name: str):
    tables = result.get("eds_tables", [])
    if not tables:
        print(c(f"\n  {result.get('message', 'No EDS table found.')}\n", "yellow"))
        return

    settings = result.get("prediction_settings")
    if settings:
        noise_txt = (f"ON ({settings.get('noise_level')})" if settings.get("noise_enabled") else "OFF")
        print(c(f"  Model: {settings.get('model')}   Noise: {noise_txt}", "dim"))

    for idx, t in enumerate(tables, start=1):
        print()
        print(c(f"  Table {idx}: ", "bold") + t.get("table_name", ""))
        print(c(f"  page {t.get('page', '-')}  ·  {len(t['spectra'])} spectra", "dim"))
        print()

        elements = t["elements"]
        has_in_stats = any(s.get("in_stats") is not None for s in t["spectra"])
        has_predictions = any(s.get("predicted_component") for s in t["spectra"])
        headers = ["Spectrum"] + (["In stats."] if has_in_stats else []) + elements \
            + (["Predicted Component"] if has_predictions else [])

        rows = []
        for s in t["spectra"]:
            row = [s["spectrum"]]
            if has_in_stats:
                row.append(s.get("in_stats") or "-")
            row.extend(fmt_val(s["values"].get(el)) for el in elements)
            if has_predictions:
                row.append(fmt_prediction(s.get("predicted_component")))
            rows.append(row)

        for label, values in t.get("statistics", {}).items():
            row = [c(label, "yellow")]
            if has_in_stats:
                row.append("")
            row.extend(fmt_val(values.get(el)) for el in elements)
            if has_predictions:
                row.append("")
            rows.append(row)

        print_table(headers, rows)

        table_pred = t.get("predicted_component")
        if table_pred and table_pred.get("top_k"):
            method = {
                "majority_vote": f"majority vote across {len(t['spectra'])} spectra, "
                                  f"{table_pred.get('agreement', 0)*100:.0f}% agreement",
            }.get(table_pred.get("method"), "")
            print(f"\n  {c('Table-level prediction:', 'bold')} "
                  f"{fmt_prediction(table_pred)}  {c('(' + method + ')', 'dim')}")
        elif len(t["spectra"]) > 1 and has_predictions:
            print(f"\n  {c('Table-level prediction:', 'bold')} "
                  f"{c('n/a - not enough per-spectrum predictions to roll up', 'dim')}")


# --------------------------------------------------------------------------
# Core pipeline
# --------------------------------------------------------------------------

def process_report(path_str: str) -> bool:
    """Run the full pipeline on one report. Returns True on success."""
    raw = path_str.strip().strip('"').strip("'")
    if not raw:
        return False

    input_path = Path(raw).expanduser()
    try:
        input_path = input_path.resolve()
    except Exception:
        pass

    if not input_path.exists():
        print(c(f"  ✘ File not found: {input_path}", "red"))
        return False

    if input_path.is_dir():
        print(c(f"  ✘ That's a folder, not a file: {input_path}", "red"))
        return False

    suffix = input_path.suffix.lower()

    progress_bar("  Checking file", duration=0.35)

    if suffix in PDF_EXTENSIONS:
        print(c(f"  Detected: PDF", "dim") + "  -> feeding directly into the EDS extractor.")
        pdf_path = input_path

    elif suffix in DOC_EXTENSIONS:
        print(c(f"  Detected: Word document", "dim") + "  -> converting to PDF first.")
        try:
            method = _pick_method("auto")
        except RuntimeError as exc:
            print(c(f"  ✘ {exc}", "red"))
            return False

        try:
            with Spinner(f"Converting to PDF ({method})"):
                pdf_path = docx_convert_file(input_path, input_path.parent, method)
        except Exception as exc:
            print(c(f"  ✘ Conversion failed: {exc}", "red"))
            return False

    else:
        print(c(f"  ✘ Unsupported file type '{suffix}'. Please provide a .pdf, .docx, or .doc file.", "red"))
        return False

    try:
        with Spinner("Extracting EDS/EDAX data"):
            result = extract_eds_tables(str(pdf_path))
    except Exception as exc:
        print(c(f"  ✘ Extraction failed: {exc}", "red"))
        return False

    if result.get("eds_tables"):
        total_spectra = sum(len(t.get("spectra", [])) for t in result["eds_tables"])
        label = ("Predicting component for "
                  f"{total_spectra} spectrum" + ("" if total_spectra == 1 else "a"))
        try:
            with Spinner(label):
                result = enrich_result_with_predictions(result)
        except Exception as exc:
            print(c(f"  ✘ Prediction failed: {exc}", "red"))
            # Fall through and still show/save the raw extraction.

    print_eds_result(result, pdf_path.name)

    json_path = pdf_path.with_suffix(".json")
    try:
        with open(json_path, "w") as f:
            json.dump(result, f, indent=2)
        print()
        print(c(f"  Saved: {json_path}", "green"))
    except Exception as exc:
        print(c(f"  ✘ Could not save JSON: {exc}", "red"))

    return True


# --------------------------------------------------------------------------
# Interactive loop
# --------------------------------------------------------------------------

def main():
    print_banner()

    # non-interactive one-shot mode: python app.py <path>
    if len(sys.argv) > 1:
        path_arg = " ".join(sys.argv[1:])
        process_report(path_arg)
        return

    print(c("  Enter the path to a report (.pdf, .docx, .doc).", "dim"))
    print(c("  Type 'q' to quit at any time.\n", "dim"))

    while True:
        try:
            path_str = input(c("  ➜ Report path: ", "bold")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if path_str.lower() in ("q", "quit", "exit"):
            break
        if not path_str:
            continue

        print()
        process_report(path_str)
        print()
        print(c("  " + "─" * 60, "dim"))
        print()

    print(c("\n  Goodbye.\n", "cyan"))


if __name__ == "__main__":
    main()
