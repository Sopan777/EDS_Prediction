"""
services/eds/extractor.py
=========================
Extracts all elemental spectra from uploaded EDS files (PDF, CSV, XLSX, JSON).
Supports multi-spectrum pooling for particles measured across multiple points.
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


def extract_all_spectra_from_file(
    file_bytes: bytes,
    filename: str,
) -> Tuple[List[Dict[str, float]], List[str], Dict[str, Any]]:
    """
    Parse uploaded file and extract ALL spectra and combined analysed elements.
    Returns: (spectra_list, analysed_elements, metadata)
    """
    fname_lower = filename.lower()
    raw_spectra: List[Dict[str, Any]] = []
    analysed_elements: List[str] = []
    metadata: Dict[str, Any] = {"filename": filename, "tables_count": 0}

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

        metadata["tables_count"] = len(eds_tables)

        # Gather spectra from the primary table or all tables
        # Usually Table 0 contains the repeat spectra for the particle
        primary_table = eds_tables[0]
        elements_set = set(e for e in primary_table.get("elements", []) if e != "Total")

        for table in eds_tables:
            for el in table.get("elements", []):
                if el != "Total":
                    elements_set.add(el)

            spectra = table.get("spectra", [])
            for s in spectra:
                vals = s.get("values", {})
                cleaned_vals = {
                    k: v for k, v in vals.items()
                    if v is not None and k != "Total"
                }
                if cleaned_vals:
                    raw_spectra.append(cleaned_vals)

        analysed_elements = sorted(list(elements_set))

    elif fname_lower.endswith(".json"):
        data = json.loads(file_bytes.decode("utf-8"))
        if isinstance(data, list):
            for item in data:
                raw_spectra.append(item.get("values", item.get("composition", item)))
        elif isinstance(data, dict):
            if "spectra" in data and isinstance(data["spectra"], list):
                for item in data["spectra"]:
                    raw_spectra.append(item.get("values", item.get("composition", item)))
            elif "composition" in data and isinstance(data["composition"], list):
                raw_spectra = data["composition"]
            else:
                raw_spectra.append(data.get("values", data.get("composition", data)))

        elements_set = set()
        for s in raw_spectra:
            elements_set.update(s.keys())
        analysed_elements = sorted(list(elements_set))

    elif fname_lower.endswith(".csv"):
        content_str = file_bytes.decode("utf-8", errors="replace")
        lines = [l.strip() for l in content_str.splitlines() if l.strip()]
        if lines:
            headers = [h.strip() for h in lines[0].split(",")]
            elements_set = set(h for h in headers if h not in ("Sr No.", "Spectrum", "Total"))
            for line in lines[1:]:
                vals = [v.strip() for v in line.split(",")]
                row_comp = {}
                for h, val in zip(headers, vals):
                    if h in ("Sr No.", "Spectrum", "Total"):
                        continue
                    try:
                        row_comp[h] = float(val)
                    except ValueError:
                        pass
                if row_comp:
                    raw_spectra.append(row_comp)
            analysed_elements = sorted(list(elements_set))

    else:
        raise ValueError(f"Unsupported file type '{filename}'. Supported: PDF, CSV, JSON.")

    if not raw_spectra:
        raise ValueError("No valid spectral compositions found in file")

    # Clean every spectrum
    cleaned_spectra: List[Dict[str, float]] = []
    for s in raw_spectra:
        clean_comp, _ = clean_numeric_composition(s, analysed_elements)
        if clean_comp:
            cleaned_spectra.append(clean_comp)

    metadata["spectra_count"] = len(cleaned_spectra)
    return cleaned_spectra, analysed_elements, metadata


def extract_composition_from_file(
    file_bytes: bytes,
    filename: str,
) -> Tuple[Dict[str, float], List[str]]:
    """Legacy single-composition helper for backwards compatibility."""
    spectra, elements, _ = extract_all_spectra_from_file(file_bytes, filename)
    return spectra[0] if spectra else {}, elements


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
