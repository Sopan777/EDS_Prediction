"""
eds_extractor.py
=================
Core extraction logic for pulling EDS / EDAX elemental-composition tables
out of material-analysis PDF reports.

The extractor never computes or modifies any number found in the PDF - it
only locates, parses and re-serialises the values exactly as printed.

Why position-anchored parsing
------------------------------
`pdftotext -layout` preserves each cell's original horizontal position with
spaces - including cells that are *blank* (an element that wasn't detected
for a given spectrum). A naive "split on runs of whitespace" parser collapses
those gaps and silently shifts every later value into the wrong column. This
extractor instead anchors each column to the header's character offsets and
slices every data row at those same offsets, so a blank cell stays blank
instead of corrupting the row. It also guards against unrelated text from a
neighbouring page column bleeding onto the same physical line (common when a
table sits beside a details box in the PDF) by only reading the leading
token out of the final column's slice.

Public API
----------
extract_eds_tables(pdf_path: str) -> dict
    Returns a dict with the shape:

    {
        "eds_tables": [
            {
                "table_name": str,
                "page": int,
                "elements": [str, ...],
                "spectra": [
                    {"spectrum": str, "in_stats": str|None, "values": {el: float|str|None, ...}},
                    ...
                ],
                "statistics": {
                    "Mean": {el: float|str|None, ...},
                    "Std. deviation": {el: float|str|None, ...},
                    "Max": {el: float|str|None, ...},
                    "Min": {el: float|str|None, ...},
                    ... (any other stat rows found, verbatim label)
                }
            },
            ...
        ]
    }

    A value is `null` when the cell was blank in the PDF (element not
    reported for that row), or the literal placeholder text (e.g. "-") when
    the PDF printed one instead of leaving the cell empty.

    If no EDS table is found anywhere in the PDF, returns:

    {
        "eds_tables": [],
        "message": "No EDS/EDAX elemental composition table was found in this PDF."
    }
"""

from __future__ import annotations

import re
import subprocess
from typing import List, Optional, Tuple


# --------------------------------------------------------------------------
# Reference data
# --------------------------------------------------------------------------

# All standard chemical element symbols (Z = 1..118). Used to validate that a
# column header found in a candidate table is really an element column and
# not some unrelated piece of text that happens to sit in the same row.
ELEMENT_SYMBOLS = {
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al",
    "Si", "P", "S", "Cl", "Ar", "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe",
    "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr",
    "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm", "Sm",
    "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Hf", "Ta", "W",
    "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn",
    "Fr", "Ra", "Ac", "Th", "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf",
    "Es", "Fm", "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds",
    "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
}

# Recognised names for the "row label" (statistics) column, mapped to the
# canonical label used in the output JSON. Matching is case-insensitive and
# ignores a trailing period.
STAT_LABEL_ALIASES = {
    "mean": "Mean",
    "average": "Mean",
    "avg": "Mean",
    "std deviation": "Std. deviation",
    "std. deviation": "Std. deviation",
    "standard deviation": "Std. deviation",
    "std dev": "Std. deviation",
    "sd": "Std. deviation",
    "max": "Max",
    "maximum": "Max",
    "min": "Min",
    "minimum": "Min",
    "median": "Median",
}

# Column-header aliases that mark the "in stats" flag column.
IN_STATS_HEADER_ALIASES = {"in stats", "instats", "in-stats", "used"}

# Column-header aliases that mark the running-total column.
TOTAL_HEADER_ALIASES = {"total"}

# A number as printed in these reports: plain float/int, optionally negative.
NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?$")
# A placeholder standing in for "no value", e.g. "-", "--", "---", "'---", "N/A".
PLACEHOLDER_RE = re.compile(r"^[\-'\u2018\u2019]{1,4}$|^n/?a$", re.IGNORECASE)
# Spectrum row identifier: an integer, optionally with a trailing letter
# (e.g. "1", "2", "3a"), on its own in the label column.
SPECTRUM_ID_RE = re.compile(r"^\d+[a-zA-Z]?$")
# A generic "leading token" - used to pull just the real value out of a
# column slice that may have unrelated text trailing after it (see module
# docstring).
LEADING_TOKEN_RE = re.compile(r"^\S+")


# --------------------------------------------------------------------------
# Low level helpers
# --------------------------------------------------------------------------

def _pdf_to_layout_text(pdf_path: str) -> str:
    """Run `pdftotext -layout` to get column-aligned text, page by page.

    Bytes are decoded explicitly as UTF-8 (rather than relying on
    subprocess's platform default, which on Windows is often cp1252 and
    raises UnicodeDecodeError on the special characters these lab reports
    commonly contain, e.g. micro signs and smart quotes).
    """
    result = subprocess.run(
        ["pdftotext", "-layout", pdf_path, "-"],
        capture_output=True,
        check=True,
    )
    return result.stdout.decode("utf-8", errors="replace")


def _tokens_with_positions(line: str) -> List[Tuple[int, int, str]]:
    """
    Split a layout-mode line into columns on runs of 2+ spaces, keeping each
    token's character offsets in the original (unstripped) line. A token may
    itself contain single spaces (e.g. "In stats.", "Std. deviation").
    """
    return [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S+(?: \S+)*", line)]


def _normalise_header_token(tok: str) -> str:
    return re.sub(r"\.$", "", tok.strip().lower())


def canonical_element_symbol(tok: str) -> Optional[str]:
    """
    Return the canonical element symbol for a header token, or None if the
    token isn't a recognised element symbol. Handles tokens carrying stray
    annotations like 'Cu(wt%)', 'Fe%', 'O ' etc., and accepts case variants
    such as 'FE' / 'fe'.

    Compound formulae are deliberately rejected rather than reduced to their
    leading element: an 'Al2O3' or 'FeO' column reports the wt% of the
    *oxide*, which is not the wt% of Al or Fe (Al is only ~52.9% of Al2O3 by
    mass), so silently treating it as the bare element would corrupt the
    composition.
    """
    stripped = tok.strip()
    # A multi-word phrase is never an element symbol. This guard matters:
    # 'In stats.' is a real column header in these reports, and its first
    # word is the valid symbol for Indium, so splitting on whitespace alone
    # would silently invent an Indium column.
    if re.search(r"\s", stripped):
        return None
    # Cut at the first annotation separator, so 'Cu(wt%)' -> 'Cu'. Stripping
    # every non-letter instead would yield 'Cuwt' and fail to match.
    head = re.split(r"[(\[{<%/,;:|]", stripped, maxsplit=1)[0]
    # Element symbols are purely alphabetic; a digit means a compound formula.
    if not head or any(ch.isdigit() for ch in head):
        return None
    bare = re.sub(r"[^A-Za-z]", "", head)
    if not bare:
        return None
    if bare in ELEMENT_SYMBOLS:
        return bare
    titled = bare[:1].upper() + bare[1:].lower()
    if titled in ELEMENT_SYMBOLS:
        return titled
    return None


def _parse_cell(raw: str):
    """
    Parse a single column slice (already isolated by character position)
    into: a float, a literal placeholder string, or None if the cell was
    blank in the source PDF. Never fabricates or computes a value.
    """
    tok = raw.strip()
    if not tok:
        return None
    if NUMBER_RE.match(tok):
        return float(tok)
    if PLACEHOLDER_RE.match(tok):
        return tok
    return None


# --------------------------------------------------------------------------
# Table name resolution
# --------------------------------------------------------------------------

def _guess_table_name(page_lines: List[str], header_idx: int, page_num: int) -> str:
    """
    Look backwards from the table header for a descriptive title:
      1. A "Project:" column value (handles multiple label:value pairs
         sharing one physical line in layout-mode text).
      2. If a "Site:" column is also found nearby, append it, since a
         single project/report commonly contains more than one
         "Site of Interest" - each with its own EDS table - and the site
         name is what actually distinguishes them.
      3. Otherwise, the first title-like line on the page.
      4. Otherwise, a generic fallback naming the page number.
    """
    project_name = None
    site_name = None

    for i in range(header_idx - 1, -1, -1):
        line = page_lines[i]
        if not line.strip():
            continue
        for _, _, col in _tokens_with_positions(line):
            if project_name is None:
                m = re.match(r"^Project\s*:\s*(.*)$", col, re.IGNORECASE)
                if m:
                    name = m.group(1).strip()
                    j = i + 1
                    if j < len(page_lines):
                        cont_tokens = _tokens_with_positions(page_lines[j])
                        if cont_tokens:
                            cont = cont_tokens[0][2]
                            if ":" not in cont and not re.match(
                                r"^(Owner|Site|Sample|Type|ID)\b", cont, re.IGNORECASE
                            ):
                                name = f"{name} {cont}".strip()
                    project_name = name
            if site_name is None:
                m = re.match(r"^Site\s*:\s*(.+)$", col, re.IGNORECASE)
                if m:
                    site_name = m.group(1).strip()
        if project_name is not None and site_name is not None:
            break
        if project_name is not None and i < header_idx - 15:
            # Project line found; stop searching further back for Site too
            break

    if project_name:
        return f"{project_name} - {site_name}" if site_name else project_name

    for line in page_lines:
        s = line.strip()
        if s and len(s) > 3 and ":" not in s[:15]:
            return s

    return f"EDS Table - Page {page_num}"


# --------------------------------------------------------------------------
# Header detection
# --------------------------------------------------------------------------

class _HeaderLayout:
    __slots__ = (
        "col_bounds", "has_in_stats", "element_cols", "has_total",
        "spectrum_idx", "in_stats_idx",
    )

    def __init__(self, col_bounds, has_in_stats, element_cols, has_total):
        self.col_bounds = col_bounds          # list of (start, end_or_None)
        self.has_in_stats = has_in_stats
        self.element_cols = element_cols      # list of (col_index, symbol) incl. Total at end if present
        self.has_total = has_total
        self.spectrum_idx = 0
        self.in_stats_idx = 1 if has_in_stats else None


def _try_parse_header(tokens: List[Tuple[int, int, str]]) -> Optional[_HeaderLayout]:
    """
    Given a candidate header row's tokens (with positions), determine
    whether it is an EDS/EDAX composition table header, and if so return
    its column layout (including character-offset boundaries for slicing
    data rows). Returns None if this isn't such a header.
    """
    if not tokens:
        return None
    if _normalise_header_token(tokens[0][2]) != "spectrum":
        return None

    idx = 1
    has_in_stats = False
    if idx < len(tokens) and _normalise_header_token(tokens[idx][2]) in IN_STATS_HEADER_ALIASES:
        has_in_stats = True
        idx += 1

    element_cols = []  # (column_index, symbol) - "Total" included as a pseudo-symbol
    has_total = False
    for i in range(idx, len(tokens)):
        norm = _normalise_header_token(tokens[i][2])
        if norm in TOTAL_HEADER_ALIASES:
            has_total = True
            element_cols.append((i, "Total"))
            continue
        sym = canonical_element_symbol(tokens[i][2])
        if sym:
            element_cols.append((i, sym))

    real_element_count = len(element_cols) - (1 if has_total else 0)
    if real_element_count < 1:
        return None  # no recognised element columns -> not an EDS table

    # Build column boundaries: column i spans from its own start offset to
    # the next column's start offset (exclusive); the last column has no
    # upper bound (handled specially at read time via leading-token parsing).
    starts = [t[0] for t in tokens]
    col_bounds = []
    for i in range(len(tokens)):
        end = starts[i + 1] if i + 1 < len(tokens) else None
        col_bounds.append((starts[i], end))

    return _HeaderLayout(col_bounds, has_in_stats, element_cols, has_total)


# --------------------------------------------------------------------------
# Row reading (position-anchored)
# --------------------------------------------------------------------------

def _read_column(line: str, bounds: Tuple[int, int]) -> str:
    """Slice `line` at the given (start, end_or_None) character bounds.
    The final column (end is None) only yields its leading token, so
    unrelated text bleeding in from a neighbouring page column (common when
    a table sits beside a details box) doesn't get swallowed into the value.
    """
    start, end = bounds
    if start >= len(line):
        return ""
    raw = line[start:end] if end is not None else line[start:]
    if end is None:
        m = LEADING_TOKEN_RE.match(raw.strip())
        return m.group() if m else ""
    return raw.strip()


def _label_region(line: str, layout: _HeaderLayout) -> str:
    """The text in the first (Spectrum / stat-label) column of a row,
    isolated by character position so it can be classified independent of
    whatever else is on the physical line."""
    end = layout.col_bounds[1][0] if len(layout.col_bounds) > 1 else layout.col_bounds[0][1]
    if end is None:
        end = len(line)
    return line[:end].strip() if end <= len(line) else line.strip()


def _read_element_values(line: str, layout: _HeaderLayout) -> dict:
    values = {}
    for col_idx, sym in layout.element_cols:
        bounds = layout.col_bounds[col_idx]
        values[sym] = _parse_cell(_read_column(line, bounds))
    return values


# --------------------------------------------------------------------------
# Core table detection / parsing
# --------------------------------------------------------------------------

def _extract_tables_from_page(page_text: str, page_num: int) -> List[dict]:
    lines = page_text.split("\n")
    tables = []
    i = 0
    n = len(lines)

    while i < n:
        tokens = _tokens_with_positions(lines[i])
        layout = _try_parse_header(tokens)
        if layout is None:
            i += 1
            continue

        elements = [sym for _, sym in layout.element_cols]

        spectra = []
        statistics = {}
        j = i + 1

        while j < n:
            line = lines[j]
            if not line.strip():
                j += 1
                continue

            label = _label_region(line, layout)

            if not label:
                # Blank in the label column but something elsewhere on the
                # line (e.g. text from a neighbouring details box bleeding
                # onto the same physical row) - not part of this table, skip.
                j += 1
                continue

            if SPECTRUM_ID_RE.match(label):
                in_stats_val = None
                if layout.has_in_stats:
                    in_stats_val = _read_column(line, layout.col_bounds[layout.in_stats_idx]) or None
                values = _read_element_values(line, layout)
                spectra.append({"spectrum": label, "in_stats": in_stats_val, "values": values})
                j += 1
                continue

            stat_key = STAT_LABEL_ALIASES.get(_normalise_header_token(label))
            if stat_key is not None:
                values = _read_element_values(line, layout)
                statistics[stat_key] = values
                j += 1
                continue

            # Unrecognised, non-blank label content ends the table (e.g.
            # "All results in weight%", a new report title, "Processing
            # option:", or the next table's own header line).
            break

        if spectra or statistics:
            table_name = _guess_table_name(lines, i, page_num)
            tables.append({
                "table_name": table_name,
                "page": page_num,
                "elements": elements,
                "spectra": spectra,
                "statistics": statistics,
            })

        i = j if j > i else i + 1

    return tables


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def extract_eds_tables(pdf_path: str) -> dict:
    """Extract every EDS/EDAX composition table from the given PDF file."""
    full_text = _pdf_to_layout_text(pdf_path)
    pages = full_text.split("\f")

    all_tables = []
    for page_num, page_text in enumerate(pages, start=1):
        if not page_text.strip():
            continue
        all_tables.extend(_extract_tables_from_page(page_text, page_num))

    if not all_tables:
        return {
            "eds_tables": [],
            "message": "No EDS/EDAX elemental composition table was found in this PDF.",
        }

    return {"eds_tables": all_tables}


# Back-compat alias: this helper was private before it was reused by
# rule_engine.normalize for input canonicalisation.
_clean_element_symbol = canonical_element_symbol


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python eds_extractor.py <path-to-pdf> [output.json]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    result = extract_eds_tables(pdf_path)
    output_json = json.dumps(result, indent=2)

    if len(sys.argv) >= 3:
        with open(sys.argv[2], "w") as f:
            f.write(output_json)
        print(f"Wrote {sys.argv[2]}")
    else:
        print(output_json)
