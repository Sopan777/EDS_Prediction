"""
indirect_engine/reference_loader.py
===================================
Loads the Indirect Material Source reference dataset from `data/Cleaning area.xlsx`
(or cached `indirect_engine/knowledge/cleaning_area_reference.json`) and computes
the exact element tolerance ranges:
  - Reference Value < 1           -> Tolerance ±25% (Min = V * 0.75, Max = V * 1.25)
  - 1 <= Reference Value <= 5     -> Tolerance ±20% (Min = V * 0.80, Max = V * 1.20)
  - Reference Value > 5           -> Tolerance ±10% (Min = V * 0.90, Max = V * 1.10)

Blank / missing elemental reference values are NEVER converted to zero.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ROOT_DIR = Path(__file__).resolve().parent.parent
EXCEL_PATH = ROOT_DIR / "data" / "Cleaning area.xlsx"
JSON_CACHE_PATH = Path(__file__).resolve().parent / "knowledge" / "cleaning_area_reference.json"


def compute_tolerance_band(ref_value: float) -> Tuple[float, float, float]:
    """
    Calculate (tolerance_fraction, min_value, max_value) for a populated reference value:
      - If reference value < 1           -> tolerance ±25% (0.25)
      - If reference value 1 to 5 (incl) -> tolerance ±20% (0.20)
      - If reference value > 5           -> tolerance ±10% (0.10)
    """
    val = float(ref_value)
    if val < 1.0:
        tol = 0.25
    elif val <= 5.0:
        tol = 0.20
    else:
        tol = 0.10
    min_val = round(val * (1.0 - tol), 6)
    max_val = round(val * (1.0 + tol), 6)
    return tol, min_val, max_val


@dataclass(frozen=True)
class IndirectElementBand:
    element: str
    reference_value: float
    tolerance: float
    min_value: float
    max_value: float

    @property
    def tolerance_pct_label(self) -> str:
        return f"±{int(round(self.tolerance * 100))}%"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "element": self.element,
            "referenceValue": self.reference_value,
            "tolerance": self.tolerance,
            "toleranceLabel": self.tolerance_pct_label,
            "minValue": round(self.min_value, 4),
            "maxValue": round(self.max_value, 4),
        }


@dataclass(frozen=True)
class IndirectPartReference:
    sn: int
    part_name: str
    location: str
    material: str
    elements: Dict[str, IndirectElementBand] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sn": self.sn,
            "partName": self.part_name,
            "location": self.location,
            "material": self.material,
            "elements": {k: v.to_dict() for k, v in self.elements.items()},
        }


_CACHED_PARTS: Optional[List[IndirectPartReference]] = None


def _clean_element_header(raw_header: Any) -> Optional[str]:
    if raw_header is None:
        return None
    s = str(raw_header).strip()
    if not s:
        return None
    s = s.replace("(%)", "").replace("%", "").strip()
    return s or None


def build_reference_from_excel(excel_path: Path = EXCEL_PATH) -> Dict[str, Any]:
    """Parse `Cleaning area.xlsx` and build the canonical indirect reference dictionary."""
    import openpyxl

    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb["Cleaning Area"]

    headers: List[Optional[str]] = [
        _clean_element_header(ws.cell(2, col).value) if col >= 6 else str(ws.cell(2, col).value or "").strip()
        for col in range(1, ws.max_column + 1)
    ]

    parts_data: List[Dict[str, Any]] = []
    families_summary: Dict[str, List[str]] = {}

    for row_idx in range(3, ws.max_row + 1):
        sn_raw = ws.cell(row_idx, 1).value
        part_raw = ws.cell(row_idx, 2).value
        loc_raw = ws.cell(row_idx, 4).value
        mat_raw = ws.cell(row_idx, 5).value

        if sn_raw is None or part_raw is None or mat_raw is None:
            continue

        sn = int(sn_raw)
        part_name = str(part_raw).strip()
        location = str(loc_raw or "").strip()
        material = str(mat_raw).strip()

        elements_dict: Dict[str, Dict[str, Any]] = {}
        for col_idx in range(6, ws.max_column + 1):
            el_sym = headers[col_idx - 1]
            if not el_sym:
                continue
            cell_val = ws.cell(row_idx, col_idx).value
            # Strictly skip blank/missing cells — never treat blank as zero
            if cell_val is None or str(cell_val).strip() == "":
                continue
            try:
                ref_val = float(cell_val)
            except (ValueError, TypeError):
                continue

            tol, min_v, max_v = compute_tolerance_band(ref_val)
            elements_dict[el_sym] = {
                "element": el_sym,
                "reference_value": ref_val,
                "tolerance": tol,
                "min_value": min_v,
                "max_value": max_v,
            }

        parts_data.append({
            "sn": sn,
            "part_name": part_name,
            "location": location,
            "material": material,
            "elements": elements_dict,
        })
        families_summary.setdefault(material, []).append(part_name)

    payload = {
        "version": "1.0.0",
        "source_file": "data/Cleaning area.xlsx",
        "scope": "Indirect Material Composition - Cleaning Area",
        "tolerance_rules": [
            {"range": "< 1", "tolerance": 0.25, "min_formula": "Value * 0.75", "max_formula": "Value * 1.25"},
            {"range": "1 to 5 (inclusive)", "tolerance": 0.20, "min_formula": "Value * 0.80", "max_formula": "Value * 1.20"},
            {"range": "> 5", "tolerance": 0.10, "min_formula": "Value * 0.90", "max_formula": "Value * 1.10"},
        ],
        "material_families": families_summary,
        "parts": parts_data,
    }

    JSON_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JSON_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def load_indirect_reference(force_reload: bool = False) -> List[IndirectPartReference]:
    """Load the 24 indirect material reference parts with their tolerance bands."""
    global _CACHED_PARTS
    if _CACHED_PARTS is not None and not force_reload:
        return _CACHED_PARTS

    if not JSON_CACHE_PATH.exists() or force_reload:
        if EXCEL_PATH.exists():
            raw_data = build_reference_from_excel(EXCEL_PATH)
        else:
            raise FileNotFoundError(f"Indirect reference file not found: {EXCEL_PATH}")
    else:
        with open(JSON_CACHE_PATH, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

    parts: List[IndirectPartReference] = []
    for item in raw_data.get("parts", []):
        el_map: Dict[str, IndirectElementBand] = {}
        for sym, ed in item.get("elements", {}).items():
            ref_v = float(ed["reference_value"])
            tol, min_v, max_v = compute_tolerance_band(ref_v)
            el_map[sym] = IndirectElementBand(
                element=sym,
                reference_value=ref_v,
                tolerance=tol,
                min_value=min_v,
                max_value=max_v,
            )
        parts.append(
            IndirectPartReference(
                sn=int(item["sn"]),
                part_name=str(item["part_name"]),
                location=str(item.get("location", "")),
                material=str(item["material"]),
                elements=el_map,
            )
        )

    _CACHED_PARTS = parts
    return parts
