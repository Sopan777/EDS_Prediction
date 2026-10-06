"""Validated Reference Spectrum Layer, Fingerprints, and Secondary Spectrum Verification Engine (Phase 4 & Section 30-31).

Implements the Reference-First Data Architecture:
  LEVEL 1 (VALIDATED): Primary validated dataset (EDS_Internal_Report_Particle_Dataset.xlsx)
  LEVEL 2 (VERIFIED SUPPLEMENTARY): Secondary records passing strict spectrum similarity validation
  LEVEL 3 (UNVERIFIED / CONFLICTING / EXCLUDED): Secondary records failing validation or lacking primary spectra
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
import math
import statistics

from isp.aggregation import SiteAggregate, sigma_eds
from isp.decode import NON_ALLOY_LIGHT_ELEMENTS
from isp.registry import COMPONENT_BY_ID, INTERNAL_COMPONENTS


@dataclass
class ElementFingerprintStats:
    element: str
    median: float
    iqr: float
    mad: float
    min_val: float
    max_val: float
    sigma_eff: float
    frequency: float
    n_sites: int


@dataclass
class ComponentReferenceFingerprint:
    component_id: str
    canonical_name: str
    trust_level: int  # 1 (Primary only) or 2 (Primary + Verified Secondary)
    n_reports: int
    n_sites: int
    n_single_candidate_sites: int
    n_spectra: int
    quality: str  # HIGH (>=5 reports), MEDIUM (2-4 reports), LOW (1 report), NONE (0 reports)
    elements: Dict[str, ElementFingerprintStats] = field(default_factory=dict)
    ratios: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)  # ratio -> (q25, median, q75)


@dataclass
class SpectrumVerificationResult:
    secondary_id: str
    secondary_component_raw: str
    mapped_component_id: Optional[str]
    reference_component_name: Optional[str]
    spectrum_similarity: float
    compatible: str  # YES / NO
    supporting_elements: List[str]
    contradicting_elements: List[str]
    reference_sites: int
    reference_reports: int
    decision: str  # ACCEPT / REVIEW / REJECT / EXCLUDED
    trust_level_assigned: int  # 2 if ACCEPT else 3
    conflict_reason: str
    element_differences: Dict[str, float] = field(default_factory=dict)


# Map secondary consolidation component names to canonical internal component IDs (name candidate only — never trusted without spectrum validation!)
SECONDARY_NAME_TO_CANONICAL: Dict[str, Optional[str]] = {
    "Armature Bolt": None,
    "Armature Guide": "ARMATURE_GUIDE",
    "Armature Plate": "ARMATURE_PLATE",
    "Armature Shim": "SHIM",
    "Armature Spring": "ARMATURE_SPRING",
    "Back Flow Tube": "BACK_FLOW_TUBE",
    "Ball Guide": None,
    "Blade Terminal": None,
    "C Shim": "SHIM",
    "CRI Injector Body": "INJECTOR_BODY",
    "CRI Sealing ring": "SEALING_RING",
    "CRI Shim": "SHIM",
    "Clamping Saddle": "CLAMPING_SADDLE",
    "DFK Shim": "SHIM",
    "DFK Spring": None,
    "Dowel Pin": None,
    "Guide Bush": "BUSHING",
    "HP Sealing": "SEALING_RING",
    "High Pressure Pipe": "HPP",
    "High pressure pipe plating": None,
    "IC Stud": "IC_STUD",
    "Locking Sleeve": "MAGNET_SLEEVE",
    "Magnet Coil": None,
    "Magnet Core": "MAGNET_CORE",
    "Magnet housing": None,
    "NR Nut": "NR_NUT",
    "Nozzle Spring": "NOZZLE_SPRING",
    "Pille": None,
    "RLS Shim": "SHIM",
    "Sealing Ring": "SEALING_RING",
    "Sleeve": "HPP_SLEEVE",
    "Support Sealing": "SEALING_RING",
    "UFK Spring": None,
    "Union Nut": "UNION_NUT",
    "VFK Shim": "SHIM",
    "Valve Nut": "NOZZLE_NUT",
    "Valve Piece": "VALVE_PIECE",
    "Valve Piston": "VALVE_PISTON",
    "Valve Spring": "VALVE_SPRING",
    "union nut plating": None,
}


def _quantiles(vals: List[float]) -> Tuple[float, float, float, float]:
    s = sorted(vals)
    n = len(s)
    med = float(statistics.median(s))
    if n == 1:
        return med, med, med, 0.0
    q25 = s[max(0, int(0.25 * (n - 1)))]
    q75 = s[min(n - 1, int(0.75 * (n - 1) + 0.5))]
    iqr = max(0.0, q75 - q25)
    mad = float(statistics.median([abs(x - med) for x in s])) * 1.4826
    return round(q25, 4), round(med, 4), round(q75, 4), round(mad, 4)


def build_reference_fingerprints(
    sites: List[SiteAggregate],
    site_candidates: Dict[str, List[str]],
    trust_level: int = 1,
) -> Dict[str, ComponentReferenceFingerprint]:
    """Build component reference fingerprints strictly from validated sites."""
    by_comp: Dict[str, List[Tuple[SiteAggregate, bool]]] = {c.component_id: [] for c in INTERNAL_COMPONENTS}
    for site in sites:
        if site.n_valid_spectra == 0 or not site.metal_basis:
            continue
        cands = site_candidates.get(site.site_uid, [])
        is_single = len(cands) == 1
        for cid in cands:
            if cid in by_comp:
                by_comp[cid].append((site, is_single))

    fingerprints: Dict[str, ComponentReferenceFingerprint] = {}
    for spec in INTERNAL_COMPONENTS:
        cid = spec.component_id
        entries = by_comp[cid]
        if not entries:
            fingerprints[cid] = ComponentReferenceFingerprint(
                component_id=cid,
                canonical_name=spec.canonical_name,
                trust_level=trust_level,
                n_reports=0,
                n_sites=0,
                n_single_candidate_sites=0,
                n_spectra=0,
                quality="NONE",
            )
            continue

        # Prefer single-candidate anchor sites when >=2 exist; otherwise use all compatible sites
        singles = [s for s, is_s in entries if is_s]
        pool = singles if len(singles) >= 2 else [s for s, _ in entries]
        reports = {s.report_id for s in pool}
        n_rep = len(reports)
        n_sites = len(pool)
        n_spec = sum(s.n_valid_spectra for s in pool)
        qual = "HIGH" if n_rep >= 5 else "MEDIUM" if n_rep >= 2 else "LOW"

        all_els = set()
        for s in pool:
            all_els.update(s.metal_basis.keys())

        el_stats: Dict[str, ElementFingerprintStats] = {}
        for el in sorted(all_els):
            vals = [s.metal_basis[el] for s in pool if el in s.metal_basis and s.metal_basis[el] > 0]
            if not vals:
                continue
            q25, med, q75, mad = _quantiles(vals)
            iqr = round(q75 - q25, 4)
            # Shrink variance floor when sample count is small
            sig_floor = sigma_eds(med, el) * (1.5 if n_rep < 3 else 1.0)
            sig_eff = round(max(mad, iqr / 1.349 if iqr > 0 else 0.0, sig_floor, 0.20), 4)
            el_stats[el] = ElementFingerprintStats(
                element=el,
                median=med,
                iqr=iqr,
                mad=mad,
                min_val=round(min(vals), 4),
                max_val=round(max(vals), 4),
                sigma_eff=sig_eff,
                frequency=round(len(vals) / n_sites, 4),
                n_sites=len(vals),
            )

        ratio_stats: Dict[str, Tuple[float, float, float]] = {}
        all_ratios = set()
        for s in pool:
            all_ratios.update(s.ratios.keys())
        for rname in sorted(all_ratios):
            rvals = [s.ratios[rname] for s in pool if rname in s.ratios]
            if rvals:
                rq25, rmed, rq75, _ = _quantiles(rvals)
                ratio_stats[rname] = (rq25, rmed, rq75)

        fingerprints[cid] = ComponentReferenceFingerprint(
            component_id=cid,
            canonical_name=spec.canonical_name,
            trust_level=trust_level,
            n_reports=n_rep,
            n_sites=n_sites,
            n_single_candidate_sites=len(singles),
            n_spectra=n_spec,
            quality=qual,
            elements=el_stats,
            ratios=ratio_stats,
        )
    return fingerprints


def verify_secondary_spectrum(
    secondary_id: str,
    secondary_comp_raw: str,
    raw_elements: Dict[str, float],
    fingerprints: Dict[str, ComponentReferenceFingerprint],
) -> SpectrumVerificationResult:
    """Compare a secondary spectrum against Level 1 Validated Reference Spectra.

    Enforces:
      - No label-based auto-merging
      - Explicit check for surface/coating site mismatch (e.g. ZnP coating vs bulk steel)
      - Robust z-distance + cosine + diagnostic element verification
    """
    clean_name = secondary_comp_raw.strip()
    mapped_id = SECONDARY_NAME_TO_CANONICAL.get(clean_name)

    if mapped_id is None:
        return SpectrumVerificationResult(
            secondary_id=secondary_id,
            secondary_component_raw=clean_name,
            mapped_component_id=None,
            reference_component_name=None,
            spectrum_similarity=0.0,
            compatible="NO",
            supporting_elements=[],
            contradicting_elements=[],
            reference_sites=0,
            reference_reports=0,
            decision="EXCLUDED",
            trust_level_assigned=3,
            conflict_reason="NO_PRIMARY_COUNTERPART: Component is not part of the validated internal-source target vocabulary.",
        )

    fp = fingerprints.get(mapped_id)
    if fp is None or fp.n_sites == 0 or not fp.elements:
        return SpectrumVerificationResult(
            secondary_id=secondary_id,
            secondary_component_raw=clean_name,
            mapped_component_id=mapped_id,
            reference_component_name=COMPONENT_BY_ID[mapped_id].canonical_name,
            spectrum_similarity=0.0,
            compatible="NO",
            supporting_elements=[],
            contradicting_elements=[],
            reference_sites=0,
            reference_reports=0,
            decision="REVIEW",
            trust_level_assigned=3,
            conflict_reason="INSUFFICIENT_PRIMARY_SPECTRA: Primary validated dataset has 0 spectrum-bearing records for this component; cannot verify spectrum similarity.",
        )

    # Compute metal-basis of secondary spectrum
    metals = {k: v for k, v in raw_elements.items() if k not in NON_ALLOY_LIGHT_ELEMENTS and v is not None and v > 0}
    msum = sum(metals.values())
    if msum <= 0:
        return SpectrumVerificationResult(
            secondary_id=secondary_id,
            secondary_component_raw=clean_name,
            mapped_component_id=mapped_id,
            reference_component_name=fp.canonical_name,
            spectrum_similarity=0.0,
            compatible="NO",
            supporting_elements=[],
            contradicting_elements=[],
            reference_sites=fp.n_sites,
            reference_reports=fp.n_reports,
            decision="REJECT",
            trust_level_assigned=3,
            conflict_reason="EMPTY_METALLIC_SPECTRUM",
        )
    sec_mb = {k: round(v * 100.0 / msum, 4) for k, v in metals.items()}

    # Check for Surface Coating vs Bulk Substrate mismatch (e.g. Zn + P > 10% when reference is bulk Fe > 95%)
    zn_p = sec_mb.get("Zn", 0.0) + sec_mb.get("P", 0.0)
    ref_zn = fp.elements.get("Zn").median if "Zn" in fp.elements else 0.0
    if zn_p > 12.0 and ref_zn < 2.0:
        diffs = {el: round(sec_mb.get(el, 0.0) - (fp.elements[el].median if el in fp.elements else 0.0), 3) for el in set(sec_mb) | set(fp.elements)}
        return SpectrumVerificationResult(
            secondary_id=secondary_id,
            secondary_component_raw=clean_name,
            mapped_component_id=mapped_id,
            reference_component_name=fp.canonical_name,
            spectrum_similarity=0.12,
            compatible="NO",
            supporting_elements=["Fe"] if "Fe" in sec_mb else [],
            contradicting_elements=["Zn", "P"],
            reference_sites=fp.n_sites,
            reference_reports=fp.n_reports,
            decision="REJECT",
            trust_level_assigned=3,
            conflict_reason=f"SITE_MISMATCH_COATING_VS_BULK: Secondary spectrum is a Zn-phosphate coating spot (Zn+P={zn_p:.1f}%), whereas primary validated reference is bulk steel.",
            element_differences=diffs,
        )

    # Compare element-by-element using robust z-score and cosine similarity
    sup: List[str] = []
    con: List[str] = []
    diffs: Dict[str, float] = {}
    weighted_z2_sum = 0.0
    weight_sum = 0.0

    universe = set(sec_mb.keys()) | set(fp.elements.keys())
    dot = 0.0
    n_sec = 0.0
    n_ref = 0.0

    for el in sorted(universe):
        v_sec = sec_mb.get(el, 0.0)
        st = fp.elements.get(el)
        v_ref = st.median if st and st.frequency >= 0.25 else 0.0
        diffs[el] = round(v_sec - (st.median if st else 0.0), 4)
        dot += v_sec * v_ref
        n_sec += v_sec * v_sec
        n_ref += v_ref * v_ref

        if st and st.frequency >= 0.35:
            # Expected or common element in primary reference
            w = 1.0 if el == "Fe" else 2.5
            z = abs(v_sec - st.median) / max(0.25, st.sigma_eff)
            weighted_z2_sum += w * min(z, 6.0) ** 2
            weight_sum += w
            if z <= 2.8:
                sup.append(el)
            else:
                con.append(el)
        elif v_sec >= 0.45:
            # Foreign element present in secondary but absent in primary reference
            sig = sigma_eds(v_sec, el)
            z = v_sec / max(0.2, sig)
            if z > 2.5:
                con.append(el)
                weighted_z2_sum += 2.0 * min(z, 6.0) ** 2
                weight_sum += 2.0

    mean_z = math.sqrt(weighted_z2_sum / max(1e-6, weight_sum))
    z_sim = math.exp(-0.35 * (mean_z ** 2))
    cos_sim = dot / math.sqrt(max(1e-9, n_sec * n_ref)) if n_sec > 0 and n_ref > 0 else 0.0
    sim = round(0.65 * z_sim + 0.35 * cos_sim, 4)

    # Decision policy
    if con and any(abs(diffs.get(e, 0.0)) > 1.0 for e in con):
        compatible = "NO"
        decision = "REJECT"
        reason = f"SPECTRUM_MISMATCH: Contradicting elements {con} (similarity={sim:.2f})."
    elif sim >= 0.78 and not con:
        if fp.n_reports >= 2 and fp.n_single_candidate_sites >= 1:
            compatible = "YES"
            decision = "ACCEPT"
            reason = f"VALIDATED_COMPATIBLE: Spectrum matches primary reference across {sup} (similarity={sim:.2f}, n_reports={fp.n_reports})."
        elif fp.n_reports >= 2:
            compatible = "YES"
            decision = "REVIEW"
            reason = f"COMPATIBLE_MULTI_CANDIDATE_REF: Spectrum matches primary multi-candidate pool (similarity={sim:.2f}), requires reviewer sign-off because primary has 0 single-candidate anchor records."
        else:
            compatible = "YES"
            decision = "REVIEW"
            reason = f"INSUFFICIENT_REFERENCE_REPORTS: Spectrum matches (similarity={sim:.2f}), but primary has only {fp.n_reports} report."
    elif sim >= 0.55:
        compatible = "NO"
        decision = "REVIEW"
        reason = f"BORDERLINE_SIMILARITY: Partial match (similarity={sim:.2f}, contradicting={con})."
    else:
        compatible = "NO"
        decision = "REJECT"
        reason = f"LOW_SPECTRUM_SIMILARITY: similarity={sim:.2f}, contradicting={con}."

    return SpectrumVerificationResult(
        secondary_id=secondary_id,
        secondary_component_raw=clean_name,
        mapped_component_id=mapped_id,
        reference_component_name=fp.canonical_name,
        spectrum_similarity=sim,
        compatible=compatible,
        supporting_elements=sup,
        contradicting_elements=con,
        reference_sites=fp.n_sites,
        reference_reports=fp.n_reports,
        decision=decision,
        trust_level_assigned=2 if decision == "ACCEPT" else 3,
        conflict_reason=reason,
        element_differences=diffs,
    )
