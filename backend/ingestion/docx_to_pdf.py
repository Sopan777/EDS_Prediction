"""
docx_to_pdf.py
==============
Convert .docx (and .doc) material-analysis reports to PDF, so they can be
fed into eds_extractor.py.

Supports two conversion backends, auto-detected in this order:
  1. Microsoft Word, via direct COM automation using `pywin32` (Windows
     only - needs Word actually installed; typical on a corporate laptop).
  2. LibreOffice / OpenOffice, via the `soffice` command line
     (cross-platform; works headless on Windows, macOS, and Linux).

You don't need both - whichever is available on your machine is used
automatically. You can also force one explicitly with --method.

Usage
-----
Convert a single file:
    python docx_to_pdf.py "C:\\reports\\CRI.I. 26-108.docx"

Convert every .docx/.doc in a folder (writes PDFs next to a mirrored
folder structure by default):
    python docx_to_pdf.py "C:\\reports" --output-dir "C:\\reports\\pdf"

Recurse into subfolders too:
    python docx_to_pdf.py "C:\\reports" --output-dir "C:\\reports\\pdf" --recursive

Convert AND immediately run the EDS extractor on every resulting PDF,
writing one JSON per PDF plus a combined JSON:
    python docx_to_pdf.py "C:\\reports" --output-dir "C:\\reports\\pdf" --extract

Force a specific backend:
    python docx_to_pdf.py "C:\\reports" --method libreoffice
"""

from __future__ import annotations

import argparse
import json
import queue
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import List, Optional

DOC_EXTENSIONS = {".docx", ".doc"}


# --------------------------------------------------------------------------
# Backend detection
# --------------------------------------------------------------------------

def _word_available() -> bool:
    try:
        import win32com.client  # noqa: F401
        return True
    except ImportError:
        return False


def _soffice_path() -> Optional[str]:
    for name in ("soffice", "soffice.exe", "libreoffice"):
        path = shutil.which(name)
        if path:
            return path
    # common Windows install locations, in case it's installed but not on PATH
    for candidate in (
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ):
        if Path(candidate).exists():
            return candidate
    return None


def _pick_method(requested: str) -> str:
    if requested == "word":
        if not _word_available():
            raise RuntimeError(
                "Method 'word' was requested but the pywin32 package isn't "
                "installed. Install it with:  pip install pywin32\n"
                "(This backend also requires Microsoft Word to be installed "
                "on this machine, and only works on Windows.)"
            )
        return "word"

    if requested == "libreoffice":
        if not _soffice_path():
            raise RuntimeError(
                "Method 'libreoffice' was requested but 'soffice' wasn't "
                "found on PATH. Install LibreOffice from "
                "https://www.libreoffice.org/download/ and make sure its "
                "'program' folder (containing soffice.exe) is on PATH."
            )
        return "libreoffice"

    # auto: prefer Word if present (usually faster + higher fidelity for
    # .docx on a Windows machine that already has Office installed),
    # otherwise fall back to LibreOffice.
    if _word_available():
        return "word"
    if _soffice_path():
        return "libreoffice"

    raise RuntimeError(
        "No conversion backend available. Install ONE of the following:\n"
        "  - pywin32, for Microsoft Word automation (Windows only, needs "
        "Word installed):   pip install pywin32\n"
        "  - LibreOffice (free, cross-platform):    "
        "https://www.libreoffice.org/download/\n"
    )


# --------------------------------------------------------------------------
# Conversion
# --------------------------------------------------------------------------

def _unblock_windows_file(path: Path) -> None:
    """
    Best-effort removal of the Windows "Mark of the Web" (the hidden
    Zone.Identifier alternate data stream Windows attaches to files
    downloaded from the internet/network). If left in place, Word opens
    such files in Protected View, which pops up a banner that automation
    can't dismiss - and since the app runs invisibly, the whole process
    just hangs forever waiting for a click that never comes.

    Silently does nothing if this isn't Windows, the stream doesn't exist,
    or it can't be removed (e.g. read-only network share) - conversion
    will still be attempted either way.
    """
    if sys.platform != "win32":
        return
    try:
        ads_path = f"{path}:Zone.Identifier"
        if Path(ads_path).exists():
            import os as _os
            _os.remove(ads_path)
    except Exception:
        pass


def _convert_with_word(docx_path: Path, out_dir: Path) -> Path:
    """
    Convert via direct Microsoft Word COM automation (pywin32), rather than
    the docx2pdf package - this gives much clearer error messages when
    something goes wrong (docx2pdf's own error reporting can surface as an
    empty string on some failures).
    """
    import pythoncom
    import win32com.client

    out_dir.mkdir(parents=True, exist_ok=True)
    target_pdf = out_dir / (docx_path.stem + ".pdf")

    _unblock_windows_file(docx_path)

    wdFormatPDF = 17

    # COM requires each thread that uses it to initialise it; harmless to
    # call even on the main thread / when already initialised.
    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0  # wdAlertsNone - suppress "keep formatting?" etc. popups
        try:
            doc = word.Documents.Open(
                str(docx_path), ReadOnly=True, AddToRecentFiles=False
            )
        except Exception as exc:
            raise RuntimeError(
                f"Word could not open the file ({exc!r}). It may be "
                f"password-protected, corrupted, or already open elsewhere."
            ) from exc

        try:
            doc.SaveAs(str(target_pdf), FileFormat=wdFormatPDF)
        except Exception as exc:
            raise RuntimeError(f"Word could not save as PDF ({exc!r}).") from exc
    finally:
        if doc is not None:
            try:
                doc.Close(False)
            except Exception:
                pass
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()

    if not target_pdf.exists():
        raise RuntimeError(f"Word conversion did not produce {target_pdf}")
    return target_pdf


def _convert_with_libreoffice(docx_path: Path, out_dir: Path) -> Path:
    soffice = _soffice_path()
    out_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            soffice, "--headless", "--norestore",
            "--convert-to", "pdf",
            "--outdir", str(out_dir),
            str(docx_path),
        ],
        capture_output=True,
        timeout=180,
    )
    target_pdf = out_dir / (docx_path.stem + ".pdf")
    if result.returncode != 0 or not target_pdf.exists():
        stderr = result.stderr.decode("utf-8", errors="replace")
        stdout = result.stdout.decode("utf-8", errors="replace")
        raise RuntimeError(
            f"LibreOffice conversion failed for {docx_path.name}:\n{stdout}\n{stderr}"
        )
    return target_pdf


def convert_file(docx_path: Path, out_dir: Path, method: str, timeout: int = 120) -> Path:
    """Convert a single .docx/.doc file to PDF. Returns the output PDF path.

    For the 'word' method, runs the COM automation on a background thread
    with a hard timeout: if Word is stuck on a hidden dialog (Protected
    View, a compatibility prompt, etc.) the script gives up and reports a
    clear error after `timeout` seconds instead of hanging forever. The
    stuck thread is left running as a daemon so the process can still exit.
    """
    if method == "word":
        result_q: "queue.Queue" = queue.Queue()

        def _worker():
            try:
                result_q.put(("ok", _convert_with_word(docx_path, out_dir)))
            except Exception as exc:  # noqa: BLE001
                result_q.put(("err", exc))

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        t.join(timeout)
        if t.is_alive():
            raise RuntimeError(
                f"Word conversion timed out after {timeout}s - it's almost "
                "certainly stuck on a hidden dialog (Protected View, a "
                "format/compatibility prompt, etc.) that automation can't "
                "click through. Open Task Manager, end any WINWORD.EXE "
                "process, then try again. If it keeps happening: right-click "
                "the file > Properties > tick 'Unblock' > OK before "
                "converting, or run this with --method libreoffice instead."
            )
        status, payload = result_q.get()
        if status == "err":
            raise payload
        return payload

    if method == "libreoffice":
        return _convert_with_libreoffice(docx_path, out_dir)
    raise ValueError(f"Unknown method: {method}")


def find_doc_files(input_path: Path, recursive: bool) -> List[Path]:
    if input_path.is_file():
        return [input_path] if input_path.suffix.lower() in DOC_EXTENSIONS else []
    pattern_fn = input_path.rglob if recursive else input_path.glob
    files = []
    for ext in DOC_EXTENSIONS:
        files.extend(pattern_fn(f"*{ext}"))
    return sorted(set(files))


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Convert .docx/.doc material-analysis reports to PDF "
                    "for use with eds_extractor.py."
    )
    parser.add_argument("input", help="A .docx/.doc file, or a folder containing them.")
    parser.add_argument(
        "--output-dir", "-o", default=None,
        help="Folder to write PDFs into. Defaults to a 'pdf' subfolder next "
             "to the input (or the same folder, for a single input file).",
    )
    parser.add_argument(
        "--recursive", "-r", action="store_true",
        help="When input is a folder, also search subfolders.",
    )
    parser.add_argument(
        "--method", choices=["auto", "word", "libreoffice"], default="auto",
        help="Conversion backend. 'auto' picks Word if available, else LibreOffice.",
    )
    parser.add_argument(
        "--extract", action="store_true",
        help="After conversion, immediately run eds_extractor.py on every "
             "resulting PDF and write JSON output next to each PDF, plus a "
             "combined 'all_eds_results.json' in the output folder.",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print full tracebacks for any conversion failures.",
    )
    parser.add_argument(
        "--timeout", type=int, default=120,
        help="Seconds to wait for the Word backend before giving up on a "
             "stuck file (default: 120). Ignored for the libreoffice backend.",
    )
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"Input not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if args.output_dir:
        out_dir = Path(args.output_dir).expanduser().resolve()
    elif input_path.is_file():
        out_dir = input_path.parent
    else:
        out_dir = input_path / "pdf"

    try:
        method = _pick_method(args.method)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    doc_files = find_doc_files(input_path, args.recursive)
    if not doc_files:
        print(f"No .docx/.doc files found under: {input_path}")
        sys.exit(0)

    print(f"Using conversion backend: {method}")
    print(f"Found {len(doc_files)} document(s). Output folder: {out_dir}\n")

    converted: List[Path] = []
    failed: List[str] = []

    for doc_path in doc_files:
        print(f"Converting: {doc_path.name} ... ", end="", flush=True)
        try:
            pdf_path = convert_file(doc_path, out_dir, method, timeout=args.timeout)
            converted.append(pdf_path)
            print(f"OK -> {pdf_path.name}")
        except Exception as exc:
            failed.append(doc_path.name)
            detail = str(exc).strip() or repr(exc)
            print(f"FAILED [{type(exc).__name__}] {detail}")
            if args.verbose:
                import traceback
                traceback.print_exc()

    print(f"\nDone: {len(converted)} converted, {len(failed)} failed.")
    if failed:
        print("Failed files:")
        for name in failed:
            print(f"  - {name}")

    if args.extract and converted:
        _run_extraction(converted, out_dir)


def _run_extraction(pdf_paths: List[Path], out_dir: Path):
    try:
        from backend.ingestion.eds_extractor import extract_eds_tables
    except ImportError:
        try:
            from eds_extractor import extract_eds_tables
        except ImportError:
            print(
                "\nSkipping extraction: eds_extractor.py wasn't found on the "
                "Python path. Place docx_to_pdf.py in the same folder as "
                "eds_extractor.py, or run this from that folder.",
                file=sys.stderr,
            )
            return

    print(f"\nRunning EDS extraction on {len(pdf_paths)} PDF(s)...")
    combined = {}
    for pdf_path in pdf_paths:
        try:
            result = extract_eds_tables(str(pdf_path))
        except Exception as exc:
            print(f"  {pdf_path.name}: extraction failed ({exc})")
            continue

        json_path = pdf_path.with_suffix(".json")
        with open(json_path, "w") as f:
            json.dump(result, f, indent=2)

        n_tables = len(result.get("eds_tables", []))
        print(f"  {pdf_path.name}: {n_tables} EDS table(s) -> {json_path.name}")
        combined[pdf_path.name] = result

    combined_path = out_dir / "all_eds_results.json"
    with open(combined_path, "w") as f:
        json.dump(combined, f, indent=2)
    print(f"\nCombined results written to: {combined_path}")


if __name__ == "__main__":
    main()
