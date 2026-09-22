"""
services/eds/extractor.py
=========================
Extracts elemental compositions from uploaded EDS files (PDF, CSV, XLSX, JSON).
"""

import io
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from backend.ingestion.eds_geometry import extract_tables
    HAVE_PDF = True
except Exception:
    try:
        from eds_geometry import extract_tables
        HAVE_PDF = True
    except Exception:
        extract_tables = None
        HAVE_PDF = False


def extract_composition_from_file(
    file_bytes: bytes,
    filename: str,
) -> Tuple[Dict[str, float], List[str]]:
    """
    Parse uploaded file and extract numeric composition and list of elements.
    Returns: (numeric_composition, analysed_elements)
    """
    fname_lower = filename.lower()
    raw_composition: Dict[str, Any] = {}
    analysed_elements: List[str] = []

    if fname_lower.endswith(".pdf"):
        if not HAVE_PDF or extract_tables is None:
            raise RuntimeError("PyMuPDF / eds_geometry is not available for PDF processing")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = Path(tmp.name)

        try:
            tables_data = extract_tables(tmp_path)
        finally:
            if tmp_path.exists():
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        eds_tables = tables_data.get("eds_tables", []) if tables_data else []
        if not eds_tables:
            raise ValueError("No EDS tables could be extracted from PDF report")

        table = eds_tables[0]
        analysed_elements = list(table.get("elements", []))
        spectra = table.get("spectra", [])
        if spectra:
            raw_composition = {
                k: v for k, v in spectra[0].get("values", {}).items()
                if v is not None and k != "Total"
            }
        else:
            raise ValueError("EDS table had no spectral data rows")

    elif fname_lower.endswith(".json"):
        data = json.loads(file_bytes.decode("utf-8"))
        if isinstance(data, dict):
            raw_composition = data.get("values", data.get("composition", data))
        elif isinstance(data, list) and len(data) > 0:
            raw_composition = data[0].get("values", data[0])
        analysed_elements = list(raw_composition.keys())

    elif fname_lower.endswith(".csv"):
        content_str = file_bytes.decode("utf-8", errors="replace")
        lines = [l.strip() for l in content_str.splitlines() if l.strip()]
        if lines:
            headers = [h.strip() for h in lines[0].split(",")]
            if len(lines) > 1:
                first_row = [v.strip() for v in lines[1].split(",")]
                for h, val in zip(headers, first_row):
                    try:
                        raw_composition[h] = float(val)
                    except ValueError:
                        pass
            analysed_elements = list(raw_composition.keys())

    else:
        raise ValueError(f"Unsupported file type '{filename}'. Supported: PDF, CSV, JSON.")

    # Clean and parse composition into numeric floats
    clean_composition, elements = clean_numeric_composition(raw_composition, analysed_elements)
    return clean_composition, elements


def clean_numeric_composition(
    raw_composition: Dict[str, Any],
    analysed_elements: Optional[List[str]] = None,
) -> Tuple[Dict[str, float], List[str]]:
    """Clean and standardize elemental composition dictionary."""
    numeric_composition: Dict[str, float] = {}
    sum_non_fe = 0.0
    has_fe_explicit = False

    for k, v in raw_composition.items():
        if k in ("Total", "In stats.", "in_stats", "Spectrum", "spectrum"):
            continue
        elem = k.strip().capitalize() if len(k) <= 2 else k.strip()
        if str(v).lower() in ("bal.", "bal", "balance", "--", "null", "none"):
            if elem == "Fe":
                has_fe_explicit = False
            continue
        try:
            val_float = float(v)
            numeric_composition[elem] = val_float
            if elem != "Fe":
                sum_non_fe += val_float
            else:
                has_fe_explicit = True
        except (ValueError, TypeError):
            continue

    # Automatic Fe balance if not explicitly specified and likely steel
    if not has_fe_explicit:
        if sum_non_fe < 98.0:
            balance_fe = round(max(0.0, 100.0 - sum_non_fe), 2)
            numeric_composition["Fe"] = balance_fe

    elements = analysed_elements or list(numeric_composition.keys())
    return numeric_composition, elements
