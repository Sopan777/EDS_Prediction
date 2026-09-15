"""
rule_engine/real_data.py
========================
Loader for the REAL measured EDS spectra in ``data/EDS Consolidation.xlsx``.

Scope: the ``Components`` sheet only. The other sheets in that workbook
(``In Process parts``, ``Raw Material``, ``Non Metallic``, ``Complaints``)
are deliberately out of scope, as are the ``CRI_Material _Composition*``
files.

Why this module exists
----------------------
``data/synthetic_eds_data.csv`` is the single-row reference table plus
multiplicative jitter: per-class means reproduce the reference row to
<0.05 wt% and every row sums to exactly 100.000. It therefore carries no
independent measurement information, and any accuracy measured on it is
circular. This sheet is the only real within-component variance available
(173 spectra, 43 labels, median 4 spectra per component).

Key semantic this loader preserves
----------------------------------
The sheet writes ``-`` for "element not measured / not reported", which is
NOT the same as a measured 0.0. That distinction is the direct cause of the
``{S: 0.2} -> Guide Bush`` failure class, so it is carried through as
``None`` rather than being coerced to zero.

Stdlib only (zipfile + xml.etree), matching the rest of ``rule_engine``.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

DEFAULT_WORKBOOK = (
    Path(__file__).resolve().parent.parent / "data" / "EDS Consolidation.xlsx"
)

SHEET_NAME = "Components"

#: Column index -> element symbol, from row 3 of the sheet.
ELEMENT_COLUMNS: Dict[int, str] = {
    5: "C", 6: "O", 7: "Al", 8: "Si", 9: "P", 10: "S", 11: "Cr", 12: "Mn",
    13: "Ni", 14: "Pb", 15: "Fe", 16: "Mo", 17: "Cu", 18: "Sn", 19: "Zn",
    20: "Au", 21: "K", 22: "N", 23: "Ca", 24: "V", 25: "W", 26: "Cl",
}

COL_SR_NO = 1
COL_COMPONENT = 2
COL_SITE = 3
COL_SPECTRUM = 4

#: Cell contents that mean "not measured", as opposed to a measured zero.
NOT_MEASURED_TOKENS = {"-", ".", "", "--", "n/a", "na", "nil"}

#: Labels in this sheet that describe a surface TREATMENT of a component
#: rather than a distinct component. Folded into the parent component as a
#: preparation variant; they are evidence for the surface-prep confounder,
#: not new classes.
SURFACE_TREATMENT_LABELS = {
    "Zinc Phosphating of CRI-BaP",
    "ZnP on NaP CRI NHB",
    "CRI Phosphated Body From Turkey",
    "CRI  Body Preclened in HNO3",
    "CRI NHB - RBTR",
    "HSX 110 NR nut",
    "Pinning Wire for DLLA",
}


@dataclass
class Spectrum:
    """One real measured EDS spectrum."""

    component: str
    site: Optional[str]
    spectrum_id: Optional[str]
    #: element -> wt%. Only elements that were actually MEASURED appear here.
    values: Dict[str, float] = field(default_factory=dict)
    #: elements explicitly marked not-measured ("-") in the sheet.
    not_measured: List[str] = field(default_factory=list)
    row: int = 0

    @property
    def total(self) -> float:
        """Sum of measured wt%. Real spectra are normalised to ~100%."""
        return sum(self.values.values())

    def get(self, element: str) -> Optional[float]:
        """Measured value, or ``None`` if the element was not measured.

        Deliberately returns ``None`` and not ``0.0`` - callers must decide
        how to treat an unmeasured element.
        """
        return self.values.get(element)


def _column_number(cell_ref: str) -> int:
    """``"AB12"`` -> 28. Excel column letters to a 1-based index."""
    letters = re.match(r"([A-Z]+)", cell_ref)
    if not letters:
        return 0
    n = 0
    for ch in letters.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n


def _shared_strings(zf: zipfile.ZipFile) -> List[str]:
    try:
        raw = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(raw)
    return [
        "".join(t.text or "" for t in si.iter(_NS + "t"))
        for si in root.iter(_NS + "si")
    ]


def _sheet_path(zf: zipfile.ZipFile, sheet_name: str) -> str:
    """Resolve a sheet name to its worksheet XML path via the rels map."""
    workbook = zf.read("xl/workbook.xml").decode("utf-8", "replace")
    rels_raw = zf.read("xl/_rels/workbook.xml.rels").decode("utf-8", "replace")
    rels = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels_raw))
    pattern = r'<sheet name="([^"]+)"[^>]*r:id="(rId\d+)"'
    for name, rid in re.findall(pattern, workbook):
        if name == sheet_name:
            target = rels.get(rid, "worksheets/sheet1.xml").lstrip("/")
            return target if target.startswith("xl/") else "xl/" + target
    raise KeyError("sheet " + repr(sheet_name) + " not found in workbook")


def _read_grid(
    zf: zipfile.ZipFile, path: str, strings: List[str]
) -> Dict[int, Dict[int, str]]:
    """Worksheet XML -> ``{row_index: {col_index: raw_text}}``, blanks omitted."""
    sheet = ET.fromstring(zf.read(path))
    grid: Dict[int, Dict[int, str]] = {}
    for row in sheet.iter(_NS + "row"):
        cells: Dict[int, str] = {}
        for c in row.iter(_NS + "c"):
            ctype = c.get("t")
            v = c.find(_NS + "v")
            inline = c.find(_NS + "is")
            value: Optional[str] = None
            if ctype == "s" and v is not None:
                idx = int(v.text or "0")
                value = strings[idx] if idx < len(strings) else None
            elif ctype == "inlineStr" and inline is not None:
                value = "".join(t.text or "" for t in inline.iter(_NS + "t"))
            elif v is not None:
                value = v.text
            if value is not None and str(value).strip() != "":
                cells[_column_number(c.get("r") or "A1")] = str(value).strip()
        if cells:
            grid[int(row.get("r") or 0)] = cells
    return grid


def load_spectra(workbook: Optional[Path] = None) -> List[Spectrum]:
    """Load every real spectrum from the ``Components`` sheet.

    ``ComponentName`` and ``Site of Intrest`` are written only on the first
    row of each group, so both are forward-filled. Site is reset when a new
    component begins, to avoid leaking one component's site onto the next.
    """
    path = Path(workbook) if workbook else DEFAULT_WORKBOOK
    if not path.exists():
        raise FileNotFoundError(
            str(path) + " not found. Recover it with:\n"
            '    git checkout -- "data/EDS Consolidation.xlsx"'
        )

    with zipfile.ZipFile(path) as zf:
        strings = _shared_strings(zf)
        grid = _read_grid(zf, _sheet_path(zf, SHEET_NAME), strings)

    out: List[Spectrum] = []
    component: Optional[str] = None
    site: Optional[str] = None

    for row_idx in sorted(grid):
        if row_idx < 4:  # rows 1-3 are the two-tier header
            continue
        cells = grid[row_idx]

        if COL_COMPONENT in cells:
            component = cells[COL_COMPONENT].strip()
            site = None  # do not inherit the previous component's site
        if COL_SITE in cells:
            raw_site = cells[COL_SITE].strip()
            site = None if raw_site.lower() in NOT_MEASURED_TOKENS else raw_site

        # A data row is identified by having a spectrum number.
        if COL_SPECTRUM not in cells or component is None:
            continue

        values: Dict[str, float] = {}
        not_measured: List[str] = []
        for col, element in ELEMENT_COLUMNS.items():
            raw = cells.get(col)
            if raw is None or raw.strip().lower() in NOT_MEASURED_TOKENS:
                not_measured.append(element)
                continue
            try:
                values[element] = float(raw)
            except ValueError:
                not_measured.append(element)

        if not values:
            continue

        out.append(
            Spectrum(
                component=component,
                site=site,
                spectrum_id=cells.get(COL_SPECTRUM),
                values=values,
                not_measured=not_measured,
                row=row_idx,
            )
        )

    return out


def group_by_component(spectra: List[Spectrum]) -> Dict[str, List[Spectrum]]:
    """Group spectra by component label, preserving sheet order."""
    grouped: Dict[str, List[Spectrum]] = {}
    for s in spectra:
        grouped.setdefault(s.component, []).append(s)
    return grouped


def is_surface_treatment(label: str) -> bool:
    """True for labels describing a surface treatment rather than a component."""
    return label.strip() in SURFACE_TREATMENT_LABELS


if __name__ == "__main__":  # pragma: no cover - manual inspection aid
    spectra = load_spectra()
    grouped = group_by_component(spectra)
    counts = sorted(((len(v), k) for k, v in grouped.items()), reverse=True)
    print(str(len(spectra)) + " real spectra across " + str(len(grouped)) + " labels")
    total_nm = sum(len(s.not_measured) for s in spectra)
    print("not-measured cells preserved: " + str(total_nm))
    print("\nspectra per label:")
    for n, label in counts:
        tag = "  [surface-treatment variant]" if is_surface_treatment(label) else ""
        print("  " + str(n).rjust(3) + "  " + label + tag)
