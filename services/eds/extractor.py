"""
services/eds/extractor.py
=========================
Extracts all elemental spectra from uploaded EDS files (XLSX, XLS, PDF, CSV, JSON).
Also provides the dynamic Excel dataset element list reader and standard Excel template generator.
Supports multi-spectrum pooling for particles measured across multiple points.
"""

import io
import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

from rule_engine.elements import canonical_element_symbol

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

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Metadata for chemical elements (name & standard atomic weight for wt% <-> at% conversion)
ELEMENT_METADATA: Dict[str, Dict[str, Any]] = {
    "Fe": {"name": "Iron", "atomic_weight": 55.845},
    "Cr": {"name": "Chromium", "atomic_weight": 51.996},
    "Ni": {"name": "Nickel", "atomic_weight": 58.693},
    "Mn": {"name": "Manganese", "atomic_weight": 54.938},
    "Si": {"name": "Silicon", "atomic_weight": 28.085},
    "C": {"name": "Carbon", "atomic_weight": 12.011},
    "Mo": {"name": "Molybdenum", "atomic_weight": 95.95},
    "Cu": {"name": "Copper", "atomic_weight": 63.546},
    "Sn": {"name": "Tin", "atomic_weight": 118.71},
    "Al": {"name": "Aluminium", "atomic_weight": 26.982},
    "Zn": {"name": "Zinc", "atomic_weight": 65.38},
    "W": {"name": "Tungsten", "atomic_weight": 183.84},
    "V": {"name": "Vanadium", "atomic_weight": 50.942},
    "Ti": {"name": "Titanium", "atomic_weight": 47.867},
    "Nb": {"name": "Niobium", "atomic_weight": 92.906},
    "Co": {"name": "Cobalt", "atomic_weight": 58.933},
    "N": {"name": "Nitrogen", "atomic_weight": 14.007},
    "O": {"name": "Oxygen", "atomic_weight": 15.999},
    "P": {"name": "Phosphorus", "atomic_weight": 30.974},
    "S": {"name": "Sulfur", "atomic_weight": 32.06},
    "Pb": {"name": "Lead", "atomic_weight": 207.2},
    "Au": {"name": "Gold", "atomic_weight": 196.967},
    "Ca": {"name": "Calcium", "atomic_weight": 40.078},
    "K": {"name": "Potassium", "atomic_weight": 39.098},
    "F": {"name": "Fluorine", "atomic_weight": 18.998},
    "Cl": {"name": "Chlorine", "atomic_weight": 35.45},
    "Mg": {"name": "Magnesium", "atomic_weight": 24.305},
    "Na": {"name": "Sodium", "atomic_weight": 22.99},
    "Ag": {"name": "Silver", "atomic_weight": 107.868},
    "Ba": {"name": "Barium", "atomic_weight": 137.327},
    "Ta": {"name": "Tantalum", "atomic_weight": 180.948},
    "Bi": {"name": "Bismuth", "atomic_weight": 208.98},
    "As": {"name": "Arsenic", "atomic_weight": 74.922},
}

# Preferred display order for dataset elements (metallurgical priority first)
PREFERRED_ELEMENT_ORDER: List[str] = [
    "Fe", "Cr", "Ni", "Mn", "Si", "C", "Mo", "Cu", "Sn", "Al", "Zn",
    "W", "V", "Ti", "Nb", "Co", "N", "O", "P", "S", "Pb", "Au",
    "Ca", "K", "F", "Cl", "Mg", "Na", "Ag", "Ba", "Ta", "Bi", "As",
]

# Known OCR / "In stats." parser header artifacts in raw tables that are not actual EDS elements
PARSER_HEADER_ARTIFACTS = {"In", "Tc", "Rh", "Ac"}

_CACHED_DATASET_ELEMENTS: Optional[List[Dict[str, Any]]] = None


def _read_excel_headers_openpyxl(xlsx_path: Path) -> List[str]:
    """Read header tokens from an Excel workbook without loading all rows."""
    headers: List[str] = []
    try:
        import openpyxl
        wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            for row in ws.iter_rows(min_row=1, max_row=5, values_only=True):
                non_empty = [str(c).strip() for c in row if c is not None and str(c).strip()]
                if len(non_empty) >= 5:
                    headers.extend(non_empty)
        wb.close()
    except Exception:
        pass
    return headers


def get_dataset_supported_elements() -> List[Dict[str, Any]]:
    """
    Dynamically read the provided Excel dataset(s) and return the exact list of
    supported EDS elements (never the full periodic table).
    """
    global _CACHED_DATASET_ELEMENTS
    if _CACHED_DATASET_ELEMENTS is not None:
        return _CACHED_DATASET_ELEMENTS

    discovered_symbols = set()
    candidate_workbooks = [
        PROJECT_ROOT / "data" / "primary" / "EDS_Internal_Report_Particle_Dataset.xlsx",
        PROJECT_ROOT / "data" / "primary" / "EDS_Consolidation_SECONDARY.xlsx",
        PROJECT_ROOT / "data" / "EDS Consolidation.xlsx",
    ]

    for wb_path in candidate_workbooks:
        if wb_path.exists():
            raw_headers = _read_excel_headers_openpyxl(wb_path)
            for h in raw_headers:
                token = h
                if token.startswith("Spectrum_1_") and "complaint" not in token:
                    token = token.replace("Spectrum_1_", "")
                sym = canonical_element_symbol(token)
                if sym and sym not in PARSER_HEADER_ARTIFACTS:
                    discovered_symbols.add(sym)

    # Fallback to trusted ISP store & component fingerprints if running in an environment without raw workbooks
    if not discovered_symbols:
        store_path = PROJECT_ROOT / "rule_engine" / "knowledge" / "trusted_isp_store.json"
        if store_path.exists():
            try:
                store_data = json.loads(store_path.read_text(encoding="utf-8"))
                for fp in (store_data.get("fingerprints") or {}).values():
                    for el in (fp.get("elements") or {}).keys():
                        if el not in PARSER_HEADER_ARTIFACTS:
                            discovered_symbols.add(el)
            except Exception:
                pass
        fp_path = PROJECT_ROOT / "rule_engine" / "knowledge" / "component_fingerprints.json"
        if fp_path.exists():
            try:
                fp_data = json.loads(fp_path.read_text(encoding="utf-8"))
                for comp in (fp_data.get("components") or {}).values():
                    for el in (comp.get("elements") or {}).keys():
                        if el not in PARSER_HEADER_ARTIFACTS:
                            discovered_symbols.add(el)
            except Exception:
                pass

    if not discovered_symbols:
        discovered_symbols = set(PREFERRED_ELEMENT_ORDER[:22])

    ordered_symbols = [el for el in PREFERRED_ELEMENT_ORDER if el in discovered_symbols]
    for el in sorted(discovered_symbols):
        if el not in ordered_symbols:
            ordered_symbols.append(el)

    result: List[Dict[str, Any]] = []
    for sym in ordered_symbols:
        meta = ELEMENT_METADATA.get(sym, {"name": sym, "atomic_weight": 50.0})
        result.append({
            "symbol": sym,
            "name": meta["name"],
            "atomic_weight": meta["atomic_weight"],
        })

    _CACHED_DATASET_ELEMENTS = result
    return result


def _extract_spectra_from_excel_bytes(
    file_bytes: bytes,
    filename: str,
) -> Tuple[List[Dict[str, float]], List[str], Dict[str, Any]]:
    """
    Extract elemental spectra from an uploaded Excel (.xlsx or .xls) file.
    Supports:
      1. Standard element-column sheets (e.g., Dhatu Bodh Template, EDS Consolidation)
      2. Report_Particle_Dataset format (Spectrum_1_<Element> columns)
      3. 'In stats.' Z-shifted EDS_Spectra rows via isp.decode.decode_row
    """
    import pandas as pd
    from isp.decode import decode_row

    allowed_symbols = {item["symbol"] for item in get_dataset_supported_elements()} | {"In"}
    bio = io.BytesIO(file_bytes)
    sheets = pd.read_excel(bio, sheet_name=None)

    raw_spectra: List[Dict[str, float]] = []
    elements_set = set()
    extracted_meta: Dict[str, Any] = {"filename": filename, "tables_count": 0}

    for sheet_name, df in sheets.items():
        if df is None or df.empty:
            continue

        # Check if header row is actually on row 1, 2, or 3 (like EDS Consolidation.xlsx)
        cols_str = [str(c).strip() for c in df.columns]
        direct_el_cols = {
            c: canonical_element_symbol(str(c).strip())
            for c in df.columns
            if canonical_element_symbol(str(c).strip()) in allowed_symbols
        }
        spec1_cols = [c for c in cols_str if c.startswith("Spectrum_1_") and "complaint" not in c]

        if len(direct_el_cols) < 2 and not spec1_cols:
            # Scan first 5 rows for a header row containing element symbols
            for r_idx in range(min(5, len(df))):
                row_vals = [str(v).strip() if pd.notna(v) else "" for v in df.iloc[r_idx].values]
                matched = [canonical_element_symbol(v) for v in row_vals if canonical_element_symbol(v) in allowed_symbols]
                if len(matched) >= 3:
                    new_df = df.iloc[r_idx + 1:].copy()
                    new_df.columns = row_vals
                    df = new_df
                    cols_str = [str(c).strip() for c in df.columns]
                    direct_el_cols = {
                        c: canonical_element_symbol(str(c).strip())
                        for c in df.columns
                        if canonical_element_symbol(str(c).strip()) in allowed_symbols
                    }
                    break

        # Case A: Report_Particle_Dataset format (Spectrum_1_<El> .. Spectrum_5_<El>)
        if spec1_cols:
            extracted_meta["tables_count"] += 1
            els = [c.replace("Spectrum_1_", "") for c in cols_str if c.startswith("Spectrum_1_") and "complaint" not in c]
            for _, row in df.iterrows():
                for k in range(1, 6):
                    cells: Dict[str, float] = {}
                    for el in els:
                        col_name = f"Spectrum_{k}_{el}"
                        if col_name in row and pd.notna(row[col_name]):
                            try:
                                cells[el] = float(row[col_name])
                            except (ValueError, TypeError):
                                pass
                    if cells:
                        dec = decode_row(cells, els)
                        if dec.status != "CORRUPT" and dec.elements:
                            raw_spectra.append(dec.elements)
                            elements_set.update(dec.elements.keys())
                if raw_spectra:
                    # Capture metadata from the first spectrum-bearing row if available
                    for m_col, m_key in [("chemistry", "chemistry"), ("surface_coating", "surface_coating"), ("location", "location")]:
                        if m_col in row and pd.notna(row[m_col]) and m_key not in extracted_meta:
                            extracted_meta[m_key] = str(row[m_col]).strip()
                    break
            if raw_spectra:
                break

        # Case B: Standard Element Columns (Template, EDS_Spectra, EDS Consolidation)
        if len(direct_el_cols) >= 1:
            from backend.ingestion.eds_extractor import STAT_LABEL_ALIASES
            extracted_meta["tables_count"] += 1
            for _, row in df.iterrows():
                # Skip Mean, Std. deviation, Max, Min summary rows if present
                is_stat_row = False
                for col in df.columns:
                    if col not in direct_el_cols and pd.notna(row.get(col)):
                        lbl = str(row.get(col)).strip().rstrip(".").lower()
                        if lbl in STAT_LABEL_ALIASES:
                            is_stat_row = True
                            break
                if is_stat_row:
                    continue

                row_cells: Dict[str, float] = {}
                has_fe_bal = False
                for orig_col, sym in direct_el_cols.items():
                    if not sym:
                        continue
                    val = row.get(orig_col)
                    if pd.isna(val):
                        continue
                    s_val = str(val).strip()
                    if not s_val or s_val in ("-", "--", ".", "n/a", "NA", "null", "None"):
                        continue
                    if s_val.lower() in ("bal.", "bal", "balance") and sym == "Fe":
                        has_fe_bal = True
                        continue
                    try:
                        f_val = float(s_val)
                        row_cells[sym] = f_val
                    except (ValueError, TypeError):
                        continue

                if not row_cells and not has_fe_bal:
                    continue

                if "In" in row_cells:
                    dec = decode_row(row_cells)
                    if dec.status != "CORRUPT" and dec.elements:
                        raw_spectra.append(dec.elements)
                        elements_set.update(dec.elements.keys())
                else:
                    if has_fe_bal and "Fe" not in row_cells:
                        other_sum = sum(v for k, v in row_cells.items() if k != "Fe")
                        row_cells["Fe"] = round(max(0.0, 100.0 - other_sum), 2)
                    if row_cells:
                        raw_spectra.append(row_cells)
                        elements_set.update(row_cells.keys())

                # Extract optional metadata columns if present in the row
                for col in df.columns:
                    c_low = str(col).strip().lower()
                    if c_low in ("declared material", "declared_material", "material body", "chemistry") and pd.notna(row.get(col)):
                        extracted_meta.setdefault("declared_material", str(row.get(col)).strip())
                    elif c_low in ("surface coating", "surface_coating", "coating") and pd.notna(row.get(col)):
                        extracted_meta.setdefault("surface_coating", str(row.get(col)).strip())
                    elif c_low in ("location", "particle location") and pd.notna(row.get(col)):
                        extracted_meta.setdefault("location", str(row.get(col)).strip())

                if len(raw_spectra) >= 50:
                    break
            if raw_spectra:
                break

    analysed_elements = [el["symbol"] for el in get_dataset_supported_elements() if el["symbol"] in elements_set]
    for el in sorted(elements_set):
        if el not in analysed_elements and el not in PARSER_HEADER_ARTIFACTS:
            analysed_elements.append(el)

    spectra_details = []
    for idx, spec_vals in enumerate(raw_spectra, start=1):
        spectra_details.append({
            "index": idx,
            "spectrum_id": str(idx),
            "label": f"Spectrum {idx}",
            "site_name": "Excel Sheet",
            "table_name": filename,
            "page": 1,
            "in_stats": "Yes",
            "analysed_elements": analysed_elements,
            "values": spec_vals,
            "raw_table_values": {el: spec_vals.get(el) for el in analysed_elements},
            "chemistry": extracted_meta.get("declared_material") or extracted_meta.get("chemistry"),
            "surface_coating": extracted_meta.get("surface_coating"),
        })
    extracted_meta["spectra_details"] = spectra_details

    return raw_spectra, analysed_elements, extracted_meta


def generate_excel_template_bytes() -> bytes:
    """
    Generate a clean, standard Excel (.xlsx) template containing columns for all
    elements supported by the dataset plus an example spectrum row.
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "EDS_Spectrum_Input"

    supported = [item["symbol"] for item in get_dataset_supported_elements()]
    headers = ["Spectrum", "Declared Material", "Surface Coating", "Location"] + supported

    header_fill = PatternFill(start_color="0F2537", end_color="0F2537", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
        col_letter = openpyxl.utils.get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = max(10, len(headers[col_idx - 1]) + 4)

    # Add a sample row so users see the expected format immediately
    sample_values = {
        "Spectrum": "Spectrum 1",
        "Declared Material": "100Cr6",
        "Surface Coating": "Nil",
        "Location": "Filter",
        "Fe": 97.60,
        "Cr": 1.50,
        "Mn": 0.45,
        "Si": 0.25,
        "C": 0.20,
    }
    row_data = [sample_values.get(h, "") for h in headers]
    ws.append(row_data)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=2, column=col_idx)
        cell.border = thin_border

    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def extract_all_spectra_from_file(
    file_bytes: bytes,
    filename: str,
) -> Tuple[List[Dict[str, float]], List[str], Dict[str, Any]]:
    """
    Parse uploaded file and extract ALL spectra (excluding Mean, Std. deviation, Min, Max).
    Supports: PDF (.pdf), Word (.docx, .doc), Excel (.xlsx, .xls), CSV (.csv), JSON (.json).
    Returns: (spectra_list, analysed_elements, metadata)
    """
    fname_lower = filename.lower()
    raw_spectra: List[Dict[str, Any]] = []
    analysed_elements: List[str] = []
    metadata: Dict[str, Any] = {
        "filename": filename,
        "tables_count": 0,
        "spectra_details": [],
        "report_metadata": {},
    }

    if fname_lower.endswith((".xlsx", ".xls")):
        raw_spectra, analysed_elements, metadata = _extract_spectra_from_excel_bytes(
            file_bytes, filename
        )
        metadata["spectra_count"] = len(raw_spectra)
        return raw_spectra, analysed_elements, metadata

    elif fname_lower.endswith((".pdf", ".docx", ".doc")):
        from backend.ingestion.eds_pipeline import resolve_to_pdf, extract_tables as pipeline_extract_tables
        from backend.ingestion.eds_extractor import STAT_LABEL_ALIASES

        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            safe_name = Path(filename).name
            input_path = tmp_dir / safe_name
            input_path.write_bytes(file_bytes)

            pdf_path = resolve_to_pdf(input_path, out_dir=tmp_dir)
            tables_data = pipeline_extract_tables(str(pdf_path))

        eds_tables = tables_data.get("eds_tables", []) if tables_data else []
        if not eds_tables:
            raise ValueError("No EDS tables could be extracted from report")

        report_meta = tables_data.get("report_metadata", {}) if tables_data else {}
        metadata["tables_count"] = len(eds_tables)
        metadata["eds_tables"] = eds_tables
        metadata["report_metadata"] = report_meta

        if report_meta.get("location"):
            metadata.setdefault("location", report_meta["location"])
        if report_meta.get("customer"):
            metadata.setdefault("customer", report_meta["customer"])
        if report_meta.get("report_no"):
            metadata.setdefault("report_no", report_meta["report_no"])
        if report_meta.get("complaint_no"):
            metadata.setdefault("complaint_no", report_meta["complaint_no"])

        elements_set = set()
        spectra_details: List[Dict[str, Any]] = []
        multi_table = len(eds_tables) > 1

        for t_idx, table in enumerate(eds_tables, start=1):
            table_elements = [
                el for el in table.get("elements", [])
                if el != "Total" and el not in PARSER_HEADER_ARTIFACTS
            ]
            for el in table_elements:
                elements_set.add(el)

            site_name = table.get("site_name") or f"Site {t_idx}"
            table_name = table.get("table_name") or site_name
            page_num = table.get("page", 1)
            table_chem = table.get("chemistry")
            table_coat = table.get("surface_coating")

            if table_chem and "chemistry" not in metadata:
                metadata["chemistry"] = table_chem
                metadata.setdefault("declared_material", table_chem)
            if table_coat and "surface_coating" not in metadata:
                metadata["surface_coating"] = table_coat

            for s in table.get("spectra", []):
                spec_id = str(s.get("spectrum", "")).strip()
                # Never extract Mean, Std. deviation, Min, Max
                norm_id = spec_id.rstrip(".").lower()
                if norm_id in STAT_LABEL_ALIASES:
                    continue

                vals = s.get("values", {})
                cleaned_vals: Dict[str, float] = {}
                for k, v in vals.items():
                    if k == "Total" or k in PARSER_HEADER_ARTIFACTS or v is None:
                        continue
                    try:
                        cleaned_vals[k] = float(v)
                    except (ValueError, TypeError):
                        pass

                if cleaned_vals:
                    raw_spectra.append(cleaned_vals)
                    global_idx = len(raw_spectra)
                    label_str = (
                        f"{site_name} (Page {page_num}) — Spectrum {spec_id}"
                        if multi_table
                        else f"{site_name} — Spectrum {spec_id}"
                    )
                    spectra_details.append({
                        "index": global_idx,
                        "spectrum_id": spec_id or str(global_idx),
                        "label": label_str,
                        "site_name": site_name,
                        "table_name": table_name,
                        "page": page_num,
                        "in_stats": s.get("in_stats"),
                        "analysed_elements": table_elements,
                        "values": cleaned_vals,
                        "raw_table_values": {el: vals.get(el) for el in table_elements},
                        "chemistry": table_chem,
                        "surface_coating": table_coat,
                    })

        analysed_elements = [
            el["symbol"] for el in get_dataset_supported_elements()
            if el["symbol"] in elements_set
        ]
        for el in sorted(elements_set):
            if el not in analysed_elements and el not in PARSER_HEADER_ARTIFACTS:
                analysed_elements.append(el)

        metadata["spectra_details"] = spectra_details
        metadata["spectra_count"] = len(raw_spectra)
        return raw_spectra, analysed_elements, metadata

    elif fname_lower.endswith(".json"):
        data = json.loads(file_bytes.decode("utf-8"))
        if isinstance(data, list):
            for item in data:
                raw_spectra.append(item.get("values", item.get("composition", item)))
        elif isinstance(data, dict):
            if "eds_tables" in data and isinstance(data["eds_tables"], list):
                for table in data["eds_tables"]:
                    for s in table.get("spectra", []):
                        raw_spectra.append(s.get("values", {}))
            elif "spectra" in data and isinstance(data["spectra"], list):
                for item in data["spectra"]:
                    raw_spectra.append(item.get("values", item.get("composition", item)))
            elif "composition" in data and isinstance(data["composition"], list):
                raw_spectra = data["composition"]
            else:
                raw_spectra.append(data.get("values", data.get("composition", data)))

        elements_set = set()
        for s in raw_spectra:
            elements_set.update(k for k in s.keys() if k != "Total")
        analysed_elements = sorted(list(elements_set))

    elif fname_lower.endswith(".csv"):
        from backend.ingestion.eds_extractor import STAT_LABEL_ALIASES
        content_str = file_bytes.decode("utf-8", errors="replace")
        lines = [l.strip() for l in content_str.splitlines() if l.strip()]
        if lines:
            headers = [h.strip() for h in lines[0].split(",")]
            elements_set = set(h for h in headers if h not in ("Sr No.", "Spectrum", "Total", "In stats."))
            for line in lines[1:]:
                vals = [v.strip() for v in line.split(",")]
                if vals and vals[0].rstrip(".").lower() in STAT_LABEL_ALIASES:
                    continue
                row_comp = {}
                for h, val in zip(headers, vals):
                    if h in ("Sr No.", "Spectrum", "Total", "In stats."):
                        continue
                    try:
                        row_comp[h] = float(val)
                    except ValueError:
                        pass
                if row_comp:
                    raw_spectra.append(row_comp)
            analysed_elements = sorted(list(elements_set))

    else:
        raise ValueError(
            f"Unsupported file type '{filename}'. Supported: PDF (.pdf), Word (.docx, .doc), Excel (.xlsx, .xls), CSV, JSON."
        )

    if not raw_spectra:
        raise ValueError("No valid spectral compositions found in file")

    cleaned_spectra: List[Dict[str, float]] = []
    spectra_details = []
    for idx, s in enumerate(raw_spectra, start=1):
        clean_comp, _ = clean_numeric_composition(s, analysed_elements, auto_balance_fe=False)
        if clean_comp:
            cleaned_spectra.append(clean_comp)
            spectra_details.append({
                "index": len(cleaned_spectra),
                "spectrum_id": str(len(cleaned_spectra)),
                "label": f"Spectrum {len(cleaned_spectra)}",
                "site_name": "Site 1",
                "table_name": filename,
                "page": 1,
                "in_stats": "Yes",
                "analysed_elements": analysed_elements,
                "values": clean_comp,
                "raw_table_values": {el: clean_comp.get(el) for el in analysed_elements},
                "chemistry": None,
                "surface_coating": None,
            })

    metadata["spectra_details"] = spectra_details
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
    auto_balance_fe: bool = True,
) -> Tuple[Dict[str, float], List[str]]:
    """Clean and standardize elemental composition dictionary."""
    numeric_composition: Dict[str, float] = {}
    sum_non_fe = 0.0
    has_fe_explicit = False
    has_fe_balance_request = False

    for k, v in raw_composition.items():
        if k in ("Total", "In stats.", "in_stats", "Spectrum", "spectrum"):
            continue
        elem = k.strip().capitalize() if len(k) <= 2 else k.strip()
        s_val = str(v).strip().lower()
        if s_val in ("bal.", "bal", "balance"):
            if elem == "Fe":
                has_fe_balance_request = True
            continue
        if s_val in ("--", "-", "null", "none", ""):
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

    # Balance Fe when explicitly requested ("Bal.") or when auto_balance_fe is enabled on manual steel inputs
    if not has_fe_explicit:
        if has_fe_balance_request:
            balance_fe = round(max(0.0, 100.0 - sum_non_fe), 2)
            numeric_composition["Fe"] = balance_fe
        elif auto_balance_fe and sum_non_fe < 95.0 and not any(m in numeric_composition for m in ("Cu", "Au", "Ag")):
            balance_fe = round(max(0.0, 100.0 - sum_non_fe), 2)
            numeric_composition["Fe"] = balance_fe

    elements = analysed_elements or list(numeric_composition.keys())
    return numeric_composition, elements
