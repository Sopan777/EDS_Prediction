"""Spectrum grouping, quality assessment, multi-spectrum aggregation, and feature generation (Phase 2 & 6)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
import math
import statistics

from isp.decode import DecodedSpectrum, NON_ALLOY_LIGHT_ELEMENTS, ATOMIC_Z


def sigma_eds(wt_pct: float, element: str = "Fe") -> float:
    """Physical EDS measurement uncertainty floor sigma(x) = sqrt(a^2 + (b*x)^2)."""
    a = 0.25 if element in {"C", "O", "N", "F"} else 0.12
    b = 0.06 if element in {"Mn", "Cr", "Si", "S", "P"} else 0.035
    return round(math.sqrt(a * a + (b * max(0.0, wt_pct)) ** 2), 4)


@dataclass
class ElementAggregate:
    element: str
    state: str  # MEASURED, BELOW_LOD, NOT_REPORTED
    median: Optional[float] = None
    mad: Optional[float] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    n_measured: int = 0
    n_spectra_reported: int = 0
    sigma: float = 0.12


@dataclass
class SiteAggregate:
    site_uid: str
    report_id: str
    n_spectra: int = 0
    n_valid_spectra: int = 0
    elements: Dict[str, ElementAggregate] = field(default_factory=dict)
    metal_basis: Dict[str, float] = field(default_factory=dict)
    metal_basis_sigma: Dict[str, float] = field(default_factory=dict)
    ratios: Dict[str, float] = field(default_factory=dict)
    dominant_element: Optional[str] = None
    dominant_metal: Optional[str] = None
    heterogeneity: float = 0.0
    quality_score: float = 0.0
    c_o_load: float = 0.0
    flags: List[str] = field(default_factory=list)
    spectra: List[DecodedSpectrum] = field(default_factory=list)


def _robust_median_mad(vals: List[float]) -> tuple[float, float]:
    med = float(statistics.median(vals))
    if len(vals) <= 1:
        return round(med, 4), 0.0
    devs = [abs(v - med) for v in vals]
    mad = float(statistics.median(devs)) * 1.4826  # Consistent normal-equivalent MAD
    return round(med, 4), round(mad, 4)


def _compute_ratios(els: Dict[str, float], mb: Dict[str, float]) -> Dict[str, float]:
    """Compute diagnostic elemental ratios without inventing missing elements."""
    ratios: Dict[str, float] = {}
    fe = mb.get("Fe", 0.0)
    if fe > 1.0:
        for num_el in ("Cr", "Mn", "Si", "Zn", "Ni", "Mo", "W", "V"):
            if num_el in mb:
                ratios[f"{num_el}/Fe"] = round(mb[num_el] / fe, 5)
    mn = mb.get("Mn", 0.0)
    if mn > 0.05 and "Si" in mb:
        ratios["Si/Mn"] = round(mb["Si"] / mn, 4)
    cr = mb.get("Cr", 0.0)
    if cr > 0.1 and "Ni" in mb:
        ratios["Ni/Cr"] = round(mb["Ni"] / cr, 4)
    cu = mb.get("Cu", 0.0)
    if cu > 1.0 and "Sn" in mb:
        ratios["Sn/Cu"] = round(mb["Sn"] / cu, 4)
    p = els.get("P", 0.0)
    if p > 0.2 and "Zn" in els:
        ratios["Zn/P"] = round(els["Zn"] / p, 4)
    return ratios


def aggregate_site_spectra(
    site_uid: str,
    report_id: str,
    spectra: List[DecodedSpectrum],
) -> SiteAggregate:
    """Aggregate 0..N spectra belonging to a single physical particle/site."""
    valid = [s for s in spectra if s.status != "CORRUPT" and s.elements]
    flags: List[str] = []
    if not valid:
        flags.append("NO_VALID_SPECTRA")
        if spectra:
            flags.append("HAS_CORRUPT_SPECTRA")
        return SiteAggregate(
            site_uid=site_uid,
            report_id=report_id,
            n_spectra=len(spectra),
            n_valid_spectra=0,
            flags=flags,
            spectra=spectra,
        )

    if len(valid) == 1:
        flags.append("SINGLE_SPECTRUM")
    if len(valid) < len(spectra):
        flags.append("PARTIAL_CORRUPT_SPECTRA")
    if any(s.status == "IN_STATS_Z_SHIFT_RECOVERED" for s in valid):
        flags.append("Z_SHIFT_DECODED")

    # Collect per-element values across valid spectra (never filling unreported as 0)
    all_els: Set[str] = set()
    for s in valid:
        all_els.update(s.elements.keys())

    el_aggs: Dict[str, ElementAggregate] = {}
    for el in sorted(all_els, key=lambda x: ATOMIC_Z.get(x, 999)):
        reported_vals = [s.elements[el] for s in valid if el in s.elements]
        pos_vals = [v for v in reported_vals if v > 0.0]
        if not reported_vals:
            el_aggs[el] = ElementAggregate(element=el, state="NOT_REPORTED")
            continue
        med, mad = _robust_median_mad(reported_vals)
        sig_floor = sigma_eds(med, el)
        eff_sigma = round(max(mad, sig_floor), 4)
        state = "MEASURED" if med > 0.0 else "BELOW_LOD"
        el_aggs[el] = ElementAggregate(
            element=el,
            state=state,
            median=med,
            mad=mad,
            min_val=round(min(reported_vals), 4),
            max_val=round(max(reported_vals), 4),
            n_measured=len(pos_vals),
            n_spectra_reported=len(reported_vals),
            sigma=eff_sigma,
        )

    # Check heterogeneity across spectra (dominant element agreement and max sigma-normalized distance)
    dom_els = [max(s.elements, key=s.elements.get) for s in valid if s.elements]
    max_z_diff = 0.0
    if len(valid) >= 2:
        for i in range(len(valid)):
            for j in range(i + 1, len(valid)):
                shared = set(valid[i].elements.keys()) | set(valid[j].elements.keys())
                z_list = []
                for el in shared:
                    if el in NON_ALLOY_LIGHT_ELEMENTS:
                        continue
                    v1 = valid[i].elements.get(el)
                    v2 = valid[j].elements.get(el)
                    if v1 is None or v2 is None:
                        continue
                    sig = sigma_eds(0.5 * (v1 + v2), el)
                    z_list.append(abs(v1 - v2) / max(0.2, sig))
                if z_list:
                    max_z_diff = max(max_z_diff, max(z_list))
    heterogeneity = round(max_z_diff, 4)
    if len(set(dom_els)) > 1 or heterogeneity > 6.0:
        flags.append("MIXED_HETEROGENEOUS_SITE")

    # Metal-basis renormalization from aggregated medians
    med_map = {el: a.median for el, a in el_aggs.items() if a.median is not None and a.median > 0}
    metals = {el: v for el, v in med_map.items() if el not in NON_ALLOY_LIGHT_ELEMENTS}
    m_sum = sum(metals.values())
    mb: Dict[str, float] = {}
    mb_sig: Dict[str, float] = {}
    if m_sum > 0:
        scale = 100.0 / m_sum
        for el, v in metals.items():
            mb[el] = round(v * scale, 4)
            raw_sig = el_aggs[el].sigma
            mb_sig[el] = round(max(sigma_eds(mb[el], el), raw_sig * scale), 4)

    dom_all = max(med_map, key=med_map.get) if med_map else None
    dom_metal = max(mb, key=mb.get) if mb else None

    co_load = round(med_map.get("C", 0.0) + med_map.get("O", 0.0), 4)
    if co_load >= 50.0:
        flags.append("HIGH_CO_CONTAMINATION_OR_OXIDE")

    ratios = _compute_ratios(med_map, mb)

    mean_q = statistics.mean(s.quality_score for s in valid)
    het_pen = max(0.6, 1.0 - 0.03 * max(0.0, heterogeneity - 2.0))
    multi_bonus = min(1.05, 0.94 + 0.04 * len(valid))
    site_q = round(min(1.0, mean_q * het_pen * multi_bonus), 4)

    return SiteAggregate(
        site_uid=site_uid,
        report_id=report_id,
        n_spectra=len(spectra),
        n_valid_spectra=len(valid),
        elements=el_aggs,
        metal_basis=mb,
        metal_basis_sigma=mb_sig,
        ratios=ratios,
        dominant_element=dom_all,
        dominant_metal=dom_metal,
        heterogeneity=heterogeneity,
        quality_score=site_q,
        c_o_load=co_load,
        flags=flags,
        spectra=spectra,
    )
