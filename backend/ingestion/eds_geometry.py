"""
eds_geometry.py
===============
Geometry-based extraction of EDS/EDAX composition tables from PDF reports.

Why this exists
---------------
``eds_extractor.py`` parses ``pdftotext -layout`` text and anchors each column
to the header's *character* offsets. That fails on these reports for two
independent reasons, both verified against the three real Material analysis
reports:

1. ``_tokens_with_positions`` splits on runs of 2+ spaces, but narrow columns in
   these tables are separated by a SINGLE space. So the header
   ``Spectrum  In stats. C  O  F  Cr Cu  Sn Total`` tokenises as
   ``['Spectrum', 'In stats. C', 'O', 'F', 'Cr Cu', 'Sn Total']`` - ``Cr``,
   ``Cu``, ``Sn`` and ``C`` are swallowed into merged tokens and never resolve
   to element symbols.
2. Even where headers tokenise cleanly, the numeric cells are not aligned to the
   header's character offsets in the text layer, so slicing at those offsets
   reads the wrong column or an empty string.

The net effect was that a table of C/O/F/Cr/Cu/Sn extracted as ``['O','F']``
with every value ``None``.

Character offsets are a proxy for geometry. This module uses the real thing:
each word's bounding box. Columns are anchored to the header words' horizontal
centres, and every data cell is assigned to its nearest anchor. That is robust
to single-space separators, to proportional fonts, and - critically - to blank
cells, because a missing value simply leaves its anchor unclaimed instead of
shifting every later value left.

Blank vs zero
-------------
A blank cell means the element was analysed for that table but not reported for
that spectrum, so it is emitted as ``None``, never ``0.0``. Preserving that
distinction is what allows the scoring layer to treat "not analysed" separately
from "measured at zero".

Requires PyMuPDF (``fitz``). ``extract_tables`` returns ``None`` when it is
unavailable, so callers can fall back to the text-based path.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from backend.ingestion.eds_extractor import (
        IN_STATS_HEADER_ALIASES,
        STAT_LABEL_ALIASES,
        TOTAL_HEADER_ALIASES,
        canonical_element_symbol,
    )
except ImportError:
    from eds_extractor import (
        IN_STATS_HEADER_ALIASES,
        STAT_LABEL_ALIASES,
        TOTAL_HEADER_ALIASES,
        canonical_element_symbol,
    )

try:  # pragma: no cover - environment dependent
    import fitz  # PyMuPDF

    _HAVE_FITZ = True
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore
    _HAVE_FITZ = False


#: Vertical gap (pt) above which two words belong to different rows. Line
#: pitch in these reports is 20-30 pt, so 4 pt is comfortably inside one line
#: while still separating adjacent ones.
ROW_GAP_PT = 4.0

#: Horizontal gap (pt) below which two header words are treated as one cell.
#: Joins multi-word labels such as "In stats." (gap ~2 pt) while leaving
#: separate element columns apart (gap >= 20 pt in these tables).
HEADER_MERGE_GAP_PT = 6.0

#: A data token is only assigned to a column anchor within this distance (pt).
#: Generous enough for right-aligned numerals sitting a few pt off the header
#: centre, tight enough that a stray token from a neighbouring text box does
#: not capture a column.
MAX_ANCHOR_DIST_PT = 22.0

NUMBER_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
SPECTRUM_ID_RE = re.compile(r"^\d+[A-Za-z]?$")

_Word = Tuple[float, float, float, str]  # (x0, x1, centre, text)


def available() -> bool:
    """True when the geometry backend can run."""
    return _HAVE_FITZ


def _rows_from_words(words: Sequence[tuple]) -> List[List[_Word]]:
    """Cluster PyMuPDF words into visual rows by vertical midpoint."""
    items = []
    for w in words:
        x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
        if text and text.strip():
            items.append(((y0 + y1) / 2.0, x0, x1, text.strip()))
    items.sort(key=lambda t: (t[0], t[1]))

    rows: List[List[_Word]] = []
    current: List[_Word] = []
    last_y: Optional[float] = None
    for mid_y, x0, x1, text in items:
        if last_y is not None and abs(mid_y - last_y) > ROW_GAP_PT:
            if current:
                rows.append(sorted(current, key=lambda t: t[0]))
            current = []
        current.append((x0, x1, (x0 + x1) / 2.0, text))
        last_y = mid_y
    if current:
        rows.append(sorted(current, key=lambda t: t[0]))
    return rows


def _merge_cells(row: Sequence[_Word]) -> List[_Word]:
    """Merge words separated by a small gap into single logical cells.

    Needed so that ``In`` + ``stats.`` becomes the label ``In stats.`` rather
    than two cells - the first of which would otherwise canonicalise to Indium
    and invent an element column.
    """
    out: List[_Word] = []
    for x0, x1, _, text in row:
        if out and x0 - out[-1][1] <= HEADER_MERGE_GAP_PT:
            px0, px1, _, ptext = out[-1]
            merged_x1 = max(px1, x1)
            out[-1] = (px0, merged_x1, (px0 + merged_x1) / 2.0, ptext + " " + text)
        else:
            out.append((x0, x1, (x0 + x1) / 2.0, text))
    return out


class _Header:
    """Column layout of one composition table."""

    def __init__(
        self,
        anchors: List[Tuple[float, str]],
        label_x_max: float,
        in_stats_x: Optional[float],
    ):
        #: (centre_x, symbol) per element column, plus "Total" if present.
        self.anchors = anchors
        #: Everything left of this x is the row-label column.
        self.label_x_max = label_x_max
        self.in_stats_x = in_stats_x

    @property
    def elements(self) -> List[str]:
        return [s for _, s in self.anchors if s != "Total"]


def _try_header(row: Sequence[_Word]) -> Optional[_Header]:
    """Return a column layout if this row is a composition-table header."""
    cells = _merge_cells(row)
    if not cells:
        return None

    spectrum_x: Optional[float] = None
    in_stats_x: Optional[float] = None
    anchors: List[Tuple[float, str]] = []

    for x0, x1, centre, text in cells:
        norm = re.sub(r"\.$", "", text.strip().lower())
        if norm == "spectrum":
            spectrum_x = x1
            continue
        if norm in IN_STATS_HEADER_ALIASES:
            in_stats_x = centre
            continue
        if norm in TOTAL_HEADER_ALIASES:
            anchors.append((centre, "Total"))
            continue
        symbol = canonical_element_symbol(text)
        if symbol:
            anchors.append((centre, symbol))

    if spectrum_x is None:
        return None
    real_elements = [s for _, s in anchors if s != "Total"]
    if len(real_elements) < 2:
        # A single recognised element is more likely a false positive than a
        # composition table.
        return None
    if len(real_elements) != len(set(real_elements)):
        return None

    anchors.sort(key=lambda t: t[0])
    # The label region must end where the next column BEGINS, not at its
    # centre. Using the centre put the "In stats." value ("Yes") inside the
    # label, so the row label read "1 Yes" and failed the spectrum-ID match -
    # silently dropping every spectrum in every table that has that column.
    boundaries = [x0 for x0, _, _, _ in cells if x0 > spectrum_x]
    label_x_max = min(boundaries) if boundaries else spectrum_x
    return _Header(anchors, label_x_max, in_stats_x)


def _assign(row: Sequence[_Word], header: _Header) -> Dict[str, Optional[float]]:
    """Assign numeric tokens in a data row to their nearest column anchor."""
    values: Dict[str, Optional[float]] = {s: None for _, s in header.anchors if s != "Total"}
    best: Dict[str, Tuple[float, float]] = {}  # symbol -> (distance, value)

    for x0, x1, centre, text in row:
        token = text.strip().rstrip("%")
        if not NUMBER_RE.match(token):
            continue
        if x1 <= header.label_x_max:
            continue  # part of the row label, not a value
        value = float(token)
        symbol, distance = None, None
        for anchor_x, sym in header.anchors:
            d = abs(centre - anchor_x)
            if distance is None or d < distance:
                symbol, distance = sym, d
        if symbol is None or symbol == "Total" or distance is None or distance > MAX_ANCHOR_DIST_PT:
            continue
        # Keep the closest claimant if two tokens compete for one column.
        prior = best.get(symbol)
        if prior is None or distance < prior[0]:
            best[symbol] = (distance, value)

    for symbol, (_, value) in best.items():
        if symbol != "Total":
            values[symbol] = value
    return values


def _row_label(row: Sequence[_Word], header: _Header) -> str:
    parts = [t for x0, x1, _, t in row if x1 <= header.label_x_max]
    return " ".join(parts).strip()


def _extract_page_context(rows: Sequence[List[_Word]], header_idx: int, page_num: int) -> Dict[str, Optional[str]]:
    """Extract Project, Site, Chemistry, and Surface Coating metadata from the page rows above the table."""
    project_name: Optional[str] = None
    site_name: Optional[str] = None
    chemistry: Optional[str] = None
    surface_coating: Optional[str] = None

    for i in range(min(header_idx, len(rows))):
        row = rows[i]
        left_words = [t for x0, _, _, t in row if x0 < 330.0]
        left_text = " ".join(left_words).strip()
        left_low = left_text.lower()

        if left_low.startswith("project:"):
            proj_val = left_text.split(":", 1)[1].strip()
            # Check next row for wrapped project title continuation
            if i + 1 < header_idx:
                next_left = " ".join(t for x0, _, _, t in rows[i + 1] if x0 < 330.0).strip()
                if next_left and ":" not in next_left and not next_left.lower().startswith(("owner", "site", "sample", "comment")):
                    proj_val = f"{proj_val} {next_left}".strip()
            project_name = proj_val
        elif left_low.startswith("site:"):
            site_name = left_text.split(":", 1)[1].strip()

        # Check right-side Particle Details table (x0 >= 340)
        right_words = [(x0, t) for x0, _, _, t in row if x0 >= 340.0]
        if right_words:
            right_label = " ".join(t for x0, t in right_words if x0 < 440.0).strip().lower()
            right_val = " ".join(t for x0, t in right_words if x0 >= 440.0).strip()
            if right_label == "chemistry" and right_val:
                if i + 1 < header_idx:
                    cont_val = " ".join(t for x0, _, _, t in rows[i + 1] if x0 >= 440.0).strip()
                    cont_lbl = " ".join(t for x0, _, _, t in rows[i + 1] if 340.0 <= x0 < 440.0).strip()
                    if cont_val and not cont_lbl:
                        right_val = f"{right_val} {cont_val}".strip()
                if right_val not in ("??", "---", "'---", "-"):
                    chemistry = right_val
            elif "coating" in right_label and right_val:
                if right_val not in ("??", "---", "'---", "-"):
                    surface_coating = right_val

    if project_name and site_name:
        table_name = f"{project_name} - {site_name}"
    elif site_name:
        table_name = f"{site_name} (Page {page_num})"
    elif project_name:
        table_name = project_name
    else:
        table_name = f"EDS Table - Page {page_num}"

    return {
        "table_name": table_name,
        "site_name": site_name or f"Page {page_num}",
        "project_name": project_name,
        "chemistry": chemistry,
        "surface_coating": surface_coating,
    }


def _extract_cover_metadata(rows: Sequence[List[_Word]]) -> Dict[str, str]:
    """Extract cover-page sample details (Report No, Date, Complaint No, Customer, Injector No, Location)."""
    meta: Dict[str, str] = {}
    for row in rows:
        full_line = " ".join(t for _, _, _, t in row).strip()
        m_rep = re.search(r"Report\s+No\.?\s*:\s*(\S+)", full_line, re.IGNORECASE)
        if m_rep:
            meta["report_no"] = m_rep.group(1).strip()
        m_date = re.search(r"Report\s+Date\s*:\s*(\S+)", full_line, re.IGNORECASE)
        if m_date:
            meta["report_date"] = m_date.group(1).strip()

        low = full_line.lower()
        if "complaint no" in low:
            val = " ".join(t for x0, _, _, t in row if x0 >= 230.0).strip()
            if val:
                meta["complaint_no"] = val
        elif low.startswith("external customer"):
            val = " ".join(t for x0, _, _, t in row if x0 >= 230.0).strip()
            if val:
                meta["customer"] = val
        elif low.startswith("injector no"):
            val = " ".join(t for x0, _, _, t in row if x0 >= 230.0).strip()
            if val:
                meta["injector_no"] = val
        elif low.startswith("location of particle"):
            val = " ".join(t for x0, _, _, t in row if x0 >= 230.0).strip()
            if val:
                meta["location"] = val
    return meta


def extract_tables(pdf_path: str) -> Optional[dict]:
    """Extract every composition table in ``pdf_path`` (spectra only; statistics rows are skipped).

    Returns ``{"eds_tables": [...], "report_metadata": {...}}``, or ``None``
    if PyMuPDF is unavailable so the caller can fall back.
    """
    if not _HAVE_FITZ:
        return None

    tables: List[dict] = []
    report_meta: Dict[str, str] = {}

    with fitz.open(pdf_path) as doc:
        for page_index in range(len(doc)):
            rows = _rows_from_words(doc[page_index].get_text("words"))
            page_num = page_index + 1

            if page_num == 1:
                report_meta.update(_extract_cover_metadata(rows))

            i = 0
            while i < len(rows):
                header = _try_header(rows[i])
                if header is None:
                    i += 1
                    continue

                spectra: List[dict] = []
                j = i + 1
                while j < len(rows):
                    row = rows[j]
                    if _try_header(row) is not None:
                        break  # the next table's header
                    label = _row_label(row, header)
                    values = _assign(row, header)
                    has_value = any(v is not None for v in values.values())

                    stat_key = STAT_LABEL_ALIASES.get(
                        re.sub(r"\.$", "", label.strip().lower())
                    )
                    if stat_key:
                        # Explicitly skip Mean, Std. deviation, Max, Min rows
                        j += 1
                        continue
                    elif SPECTRUM_ID_RE.match(label) and has_value:
                        in_stats = None
                        if header.in_stats_x is not None:
                            for x0, x1, centre, text in row:
                                if (
                                    abs(centre - header.in_stats_x)
                                    <= MAX_ANCHOR_DIST_PT
                                    and not NUMBER_RE.match(text.strip())
                                ):
                                    in_stats = text.strip()
                                    break
                        spectra.append(
                            {
                                "spectrum": label,
                                "in_stats": in_stats,
                                "values": values,
                            }
                        )
                    elif has_value and not label:
                        # Values with no row label: a continuation artefact.
                        pass
                    elif label and not has_value and spectra:
                        # Prose after the table body (e.g. "All results in
                        # weight%") ends it.
                        if not SPECTRUM_ID_RE.match(label) and not stat_key:
                            break
                    j += 1

                if spectra:
                    ctx = _extract_page_context(rows, i, page_num)
                    tables.append(
                        {
                            "table_name": ctx["table_name"],
                            "site_name": ctx["site_name"],
                            "project_name": ctx["project_name"],
                            "page": page_num,
                            "chemistry": ctx["chemistry"],
                            "surface_coating": ctx["surface_coating"],
                            "elements": header.elements,
                            "spectra": spectra,
                        }
                    )
                i = max(j, i + 1)

    return {"eds_tables": tables, "report_metadata": report_meta}


if __name__ == "__main__":  # pragma: no cover - manual inspection aid
    import glob
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    targets = sys.argv[1:] or sorted(glob.glob("*.pdf"))
    for path in targets:
        result = extract_tables(path)
        print("=" * 74)
        print(path)
        if result is None:
            print("  PyMuPDF unavailable")
            continue
        print(json.dumps(result, indent=2)[:4000])
