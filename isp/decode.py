"""Spectrum decoder and three-state representation (Phase 1 & Phase 2).

Mathematically proven structure of `EDS_Internal_Report_Particle_Dataset.xlsx`:
In Oxford INCA / Aztec EDS tables, the header row is:
    Spectrum | In stats. | <Element_1> | <Element_2> | ... | <Element_k> | Total
where `<Element_1> ... <Element_k>` are strictly ordered by Atomic Number (Z).
When the upstream report extractor parsed the table:
  1. "In" inside "In stats." was matched as Indium ("In"), and "Total" was ignored,
     producing k+1 headers: ['In', E_1, E_2, ..., E_k] in Z-order.
  2. In each spectrum row ("Spectrum N | Yes | v_1 | v_2 | ... | v_k | 100.00"),
     the k+1 floats [v_1, ..., v_k, 100.00] were zipped with ['In', E_1, ..., E_k].
  3. Reconstructs the exact original (E_i, v_i) pairs by sorting populated non-'In'
     headers by Atomic Number Z:
       - E_1 receives the value stored under 'In'
       - E_2 receives the value stored under E_1
       - ...
       - E_k receives the value stored under E_{k-1}
       - The value stored under E_k is the reported Total (100.00).

Across all 188 extracted spectra in the primary dataset:
  - 184 / 184 rows with 'In' satisfy E_k == 100.00 and sum(v_1..v_k) == 100.00.
  - 2 / 4 rows without 'In' already carry native labels summing to 100.00.
  - 2 / 4 rows without 'In' (Row 459 Spec 2 & 3) have corrupt column alignment
    (sum = 202.0, 204.0) and are quarantined as CORRUPT.

No missing element is ever converted to zero. Raw extracted cells are preserved alongside
the decoded representation.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import math

ATOMIC_Z: Dict[str, int] = {
    "C": 6, "N": 7, "O": 8, "F": 9, "Na": 11, "Mg": 12, "Al": 13, "Si": 14,
    "P": 15, "S": 16, "Cl": 17, "K": 19, "Ca": 20, "Ti": 22, "V": 23, "Cr": 24,
    "Mn": 25, "Fe": 26, "Co": 27, "Ni": 28, "Cu": 29, "Zn": 30, "As": 33,
    "Nb": 41, "Mo": 42, "Tc": 43, "Rh": 45, "Ag": 47, "In": 49, "Sn": 50,
    "Ba": 56, "Ta": 73, "W": 74, "Au": 79, "Pb": 82, "Bi": 83, "Ac": 89,
}

NON_ALLOY_LIGHT_ELEMENTS = {"C", "O", "N", "F", "K", "Ca", "Na", "Cl", "Mg"}

TOTAL_TOL = 0.05
SUM_TOL = 1.5


@dataclass
class DecodedSpectrum:
    """Represents a single spectrum with raw cells preserved and three-state values."""
    raw_cells: Dict[str, float] = field(default_factory=dict)
    elements: Dict[str, float] = field(default_factory=dict)
    element_states: Dict[str, str] = field(default_factory=dict)  # MEASURED, BELOW_LOD, NOT_REPORTED
    metal_basis: Dict[str, float] = field(default_factory=dict)
    total: Optional[float] = None
    sum_wt: float = 0.0
    status: str = "CORRUPT"  # IN_STATS_Z_SHIFT_RECOVERED | NATIVE_LABELS | CORRUPT
    quality_score: float = 0.0
    c_o_load: float = 0.0
    note: str = ""


def _compute_metal_basis(elements: Dict[str, float]) -> Dict[str, float]:
    metals = {el: val for el, val in elements.items() if el not in NON_ALLOY_LIGHT_ELEMENTS and val > 0}
    s = sum(metals.values())
    if s <= 0:
        return {}
    return {el: round((val / s) * 100.0, 4) for el, val in metals.items()}


def _compute_quality(elements: Dict[str, float], sum_wt: float, total: Optional[float], status: str) -> float:
    if status == "CORRUPT" or not elements:
        return 0.0
    sum_dev = abs(sum_wt - 100.0)
    sum_factor = max(0.0, 1.0 - (sum_dev / 5.0))
    co = elements.get("C", 0.0) + elements.get("O", 0.0)
    # High C+O (>50%) on metallic parts indicates heavy surface oxide/carbon tape contamination
    metals_sum = sum(v for k, v in elements.items() if k not in NON_ALLOY_LIGHT_ELEMENTS)
    if metals_sum > 5.0:
        co_penalty = max(0.3, 1.0 - 0.5 * (co / 100.0))
    else:
        co_penalty = 0.85  # Non-metallic / oxide spectrum
    total_bonus = 1.0 if total is not None and abs(total - 100.0) <= TOTAL_TOL else 0.92
    return round(min(1.0, sum_factor * co_penalty * total_bonus), 4)


def decode_row(cells: Dict[str, float], all_known_elements: Optional[List[str]] = None) -> DecodedSpectrum:
    """Decode a spectrum row while preserving raw_cells and explicit three-state missingness."""
    clean_cells: Dict[str, float] = {}
    for h, v in cells.items():
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            clean_cells[h] = float(v)
    if not clean_cells:
        return DecodedSpectrum(note="empty")

    if "In" in clean_cells:
        z_keys = sorted([e for e in clean_cells if e != "In"], key=lambda x: ATOMIC_Z.get(x, 999))
        ordered_keys = ["In"] + z_keys
        ordered_vals = [clean_cells[e] for e in ordered_keys]
        # Single-element spectrum e.g. {'In': 100.0, 'Fe': 100.0} -> Fe=100.0, Total=100.0
        if len(z_keys) >= 1 and abs(ordered_vals[-1] - 100.0) <= TOTAL_TOL:
            els = dict(zip(z_keys, ordered_vals[:-1]))
            tot = ordered_vals[-1]
            s = round(sum(els.values()), 4)
            ok = abs(s - 100.0) <= SUM_TOL
            status = "IN_STATS_Z_SHIFT_RECOVERED" if ok else "CORRUPT"
            note = "" if ok else f"sum={s:.2f}"
        else:
            els = {}
            tot = None
            s = round(sum(clean_cells.values()), 4)
            status = "CORRUPT"
            note = "In present but last Z-ordered value != 100.0"
    else:
        s = round(sum(clean_cells.values()), 4)
        has_100 = any(abs(v - 100.0) <= TOTAL_TOL for v in clean_cells.values())
        if abs(s - 100.0) <= SUM_TOL and not (len(clean_cells) > 1 and has_100):
            els = dict(clean_cells)
            tot = None
            status = "NATIVE_LABELS"
            note = ""
        else:
            els = dict(clean_cells)
            tot = None
            status = "CORRUPT"
            note = f"no In and invalid sum={s:.2f}"

    states: Dict[str, str] = {}
    universe = all_known_elements if all_known_elements else list(ATOMIC_Z.keys())
    for el in universe:
        if el in els:
            states[el] = "MEASURED" if els[el] > 0.0 else "BELOW_LOD"
        else:
            states[el] = "NOT_REPORTED"

    co_load = round(els.get("C", 0.0) + els.get("O", 0.0), 4) if els else 0.0
    mb = _compute_metal_basis(els) if status != "CORRUPT" else {}
    q = _compute_quality(els, s, tot, status)
    return DecodedSpectrum(
        raw_cells=clean_cells,
        elements=els,
        element_states=states,
        metal_basis=mb,
        total=tot,
        sum_wt=s,
        status=status,
        quality_score=q,
        c_o_load=co_load,
        note=note,
    )
