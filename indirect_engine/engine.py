"""
indirect_engine/engine.py
=========================
Standalone Two-Stage Rule Engine for Probable Indirect Material Source Prediction.

Prediction Hierarchy:
  EDS Elemental Composition
    -> Stage 1: Indirect Material Family (SS 304, SS 301, Mn Steel, AiSi 410, EN 31, CS)
    -> Stage 2: Probable Indirect Source / Part Name (from Cleaning area.xlsx)

This engine is completely independent from the Direct / Injector Component
prediction system (`rule_engine/` and `isp/`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from indirect_engine.reference_loader import (
    IndirectElementBand,
    IndirectPartReference,
    load_indirect_reference,
)


# Light / non-metallic surface elements in EDS that dilute metallic wt%
LIGHT_AND_SURFACE_ELEMENTS: Set[str] = {
    "C", "O", "N", "F", "Ca", "Na", "K", "Cl", "Mg", "S", "P", "B"
}

# Human-readable labels for the 6 Cleaning Area Indirect Material Classifications
INDIRECT_FAMILY_LABELS: Dict[str, str] = {
    "SS 304": "Austenitic Stainless Steel (SS 304)",
    "SS 301": "Austenitic Stainless Steel (SS 301)",
    "Mn Steel": "High-Manganese Cr-Mn Austenitic Steel (Mn Steel)",
    "AiSi 410": "Martensitic / Cr Alloy Steel (AiSi 410)",
    "EN 31": "High-Carbon Chromium Steel (EN 31)",
    "CS": "Carbon Steel (CS)",
}


@dataclass
class IndirectElementCheck:
    element: str
    reference_value: float
    tolerance: float
    min_value: float
    max_value: float
    measured_value: Optional[float]
    status: str  # "within_tolerance" | "outside_tolerance" | "missing"
    deviation_pct: Optional[float] = None
    score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "element": self.element,
            "referenceValue": round(self.reference_value, 4),
            "tolerance": self.tolerance,
            "toleranceLabel": f"±{int(round(self.tolerance * 100))}%",
            "minValue": round(self.min_value, 4),
            "maxValue": round(self.max_value, 4),
            "measuredValue": round(self.measured_value, 4) if self.measured_value is not None else None,
            "status": self.status,
            "deviationPct": round(self.deviation_pct, 2) if self.deviation_pct is not None else None,
            "score": round(self.score, 4),
        }


@dataclass
class IndirectPartCandidate:
    sn: int
    part_name: str
    location: str
    material: str
    compatibility: float  # 0.0 to 1.0
    compatibility_pct: int  # 0 to 100
    within_tolerance_elements: List[str] = field(default_factory=list)
    outside_tolerance_elements: List[str] = field(default_factory=list)
    missing_elements: List[str] = field(default_factory=list)
    contradictory_elements: List[str] = field(default_factory=list)
    element_checks: List[IndirectElementCheck] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sn": self.sn,
            "partName": self.part_name,
            "location": self.location,
            "material": self.material,
            "materialLabel": INDIRECT_FAMILY_LABELS.get(self.material, self.material),
            "compatibility": round(self.compatibility, 4),
            "compatibilityPct": self.compatibility_pct,
            "withinToleranceElements": self.within_tolerance_elements,
            "outsideToleranceElements": self.outside_tolerance_elements,
            "missingElements": self.missing_elements,
            "contradictoryElements": self.contradictory_elements,
            "elementChecks": [chk.to_dict() for chk in self.element_checks],
            "notes": self.notes,
        }


def _prepare_dual_basis_composition(
    composition: Dict[str, Any],
) -> Tuple[Dict[str, float], Dict[str, float], bool]:
    """
    Clean measured EDS dictionary and compute:
      1. raw_wt: as-measured numeric wt% (with 'Fe': 'Bal.' resolved if present)
      2. metal_wt: renormalized over metallic elements (excluding C, O, N, F, etc.)
         when light elements are present or total wt% >= 75%.
      3. has_light_dilution: True if C/O/N/F sum to > 1.5 wt%.
    Blank / None / 0 values are omitted so missing elements are never treated as 0.
    """
    raw_wt: Dict[str, float] = {}
    has_fe_bal = False

    for k, v in (composition or {}).items():
        sym = str(k).replace("(%)", "").replace("%", "").strip()
        if not sym:
            continue
        if sym == "Fe" and isinstance(v, str) and v.strip().lower().startswith("bal"):
            has_fe_bal = True
            continue
        if v is None or str(v).strip() == "":
            continue
        try:
            num = float(v)
        except (ValueError, TypeError):
            continue
        if num > 0.0:
            raw_wt[sym] = num

    sum_others = sum(raw_wt.values())
    if has_fe_bal and "Fe" not in raw_wt:
        fe_rem = max(0.0, 100.0 - sum_others)
        if fe_rem > 0.0:
            raw_wt["Fe"] = round(fe_rem, 4)

    light_sum = sum(v for k, v in raw_wt.items() if k in LIGHT_AND_SURFACE_ELEMENTS)
    metal_only = {k: v for k, v in raw_wt.items() if k not in LIGHT_AND_SURFACE_ELEMENTS}
    metal_sum = sum(metal_only.values())

    has_light_dilution = light_sum > 1.5
    metal_wt: Dict[str, float] = {}

    # Renormalize to metal basis only if light elements diluted the reading
    # and there is a meaningful metallic matrix (metal_sum >= 35%).
    if has_light_dilution and metal_sum >= 35.0:
        for k, v in metal_only.items():
            metal_wt[k] = round((v / metal_sum) * 100.0, 4)
    else:
        metal_wt = dict(raw_wt)

    return raw_wt, metal_wt, has_light_dilution


def classify_indirect_material_family(
    raw_wt: Dict[str, float],
    metal_wt: Dict[str, float],
) -> Tuple[Optional[str], List[str], str]:
    """
    STAGE 1 — Determine the most probable Indirect Material Family from the
    measured EDS composition.

    Returns:
      (primary_family, candidate_families, stage1_reason)
      If incompatible with all Cleaning Area material families, returns (None, [], reason).
    """
    if not raw_wt and not metal_wt:
        return None, [], "No elemental composition available for indirect material classification."

    # Use metal-basis values for alloy classification
    cr = metal_wt.get("Cr", raw_wt.get("Cr", 0.0))
    ni = metal_wt.get("Ni", raw_wt.get("Ni", 0.0))
    mn = metal_wt.get("Mn", raw_wt.get("Mn", 0.0))
    fe = metal_wt.get("Fe", raw_wt.get("Fe", 0.0))
    cu = metal_wt.get("Cu", raw_wt.get("Cu", 0.0))
    sn = metal_wt.get("Sn", raw_wt.get("Sn", 0.0))
    au = metal_wt.get("Au", raw_wt.get("Au", 0.0))
    w = metal_wt.get("W", raw_wt.get("W", 0.0))
    mo = metal_wt.get("Mo", raw_wt.get("Mo", 0.0))
    v = metal_wt.get("V", raw_wt.get("V", 0.0))
    zn = metal_wt.get("Zn", raw_wt.get("Zn", 0.0))
    al = metal_wt.get("Al", raw_wt.get("Al", 0.0))
    si = metal_wt.get("Si", raw_wt.get("Si", 0.0))

    # 1. Disqualify non-ferrous alloys (Cu-Sn bronze, Brass, Au contact, Ni-base superalloy, Al-Si ceramic)
    if cu >= 15.0 or sn >= 1.5:
        return (
            None,
            [],
            f"Cu-rich / bronze composition (Cu={cu:.2f}%, Sn={sn:.2f}%) does not belong to any Cleaning Area indirect steel family.",
        )
    if au >= 10.0:
        return (
            None,
            [],
            f"Au-rich composition (Au={au:.2f}%) does not belong to any Cleaning Area indirect material family.",
        )
    if ni >= 35.0:
        return (
            None,
            [],
            f"Ni-base alloy (Ni={ni:.2f}%) does not belong to any Cleaning Area indirect material family.",
        )
    if al >= 15.0 or si >= 15.0:
        return (
            None,
            [],
            f"Ceramic / Al-Si composition (Al={al:.2f}%, Si={si:.2f}%) does not belong to any Cleaning Area indirect material family.",
        )

    # 2. Disqualify High-Speed Tool Steels (W, high Mo, high V) & Spring Steels (high Si > 1.1% with Cr)
    if w >= 1.5 or mo >= 1.5 or v >= 1.0:
        return (
            None,
            [],
            f"High-speed / tool steel signature (W={w:.2f}%, Mo={mo:.2f}%, V={v:.2f}%) is not present in Cleaning Area indirect sources.",
        )
    if si >= 1.15 and 0.4 <= cr <= 1.2:
        return (
            None,
            [],
            f"Si-Cr spring steel signature (Si={si:.2f}%, Cr={cr:.2f}%) does not match any Cleaning Area indirect material family.",
        )

    # 3. Disqualify heavy Zn / ZnP coating layers where bulk indirect alloy is masked
    if zn >= 15.0:
        return (
            None,
            [],
            f"Dominant Zn coating layer (Zn={zn:.2f}%) masks substrate; no Zn-galvanized indirect source in Cleaning Area reference.",
        )

    # 4. Require at least one discriminating alloy element (Cr, Ni, Mn) or explicit Fe + Zn/Mn
    if cr == 0.0 and ni == 0.0 and mn == 0.0:
        return (
            None,
            [],
            "Insufficient discriminating alloy elements (Cr, Ni, Mn not detected) to classify Indirect Material Family.",
        )

    # 5. Classify among the 6 Cleaning Area Indirect Material Families:
    #    - Mn Steel: Cr ~13.5-16.5%, Mn ~7.8-9.5%, Ni ~0.7-1.1%, Cu ~1.1-1.7%
    if 11.5 <= cr <= 17.5 and mn >= 5.0:
        return (
            "Mn Steel",
            ["Mn Steel"],
            f"High Cr ({cr:.2f}%) + High Mn ({mn:.2f}%) matches Indirect Family 'Mn Steel'.",
        )

    #    - Austenitic Stainless Steels: SS 304 vs SS 301
    #      SS 304: Cr ~15.75-20.15%, Ni ~7.1-10.65%, Mn ~0.81-2.33%
    #      SS 301: Cr ~15.89-19.43%, Ni ~6.88-8.40%, Mn ~0.075-0.125%
    if 14.0 <= cr <= 22.5 and 5.5 <= ni <= 12.5:
        if 0.0 < mn <= 0.35:
            return (
                "SS 301",
                ["SS 301", "SS 304"],
                f"18Cr-8Ni austenitic stainless signature (Cr={cr:.2f}%, Ni={ni:.2f}%) with low Mn ({mn:.2f}%) matches 'SS 301'.",
            )
        return (
            "SS 304",
            ["SS 304", "SS 301"],
            f"18Cr-8Ni austenitic stainless signature (Cr={cr:.2f}%, Ni={ni:.2f}%, Mn={mn:.2f}%) matches 'SS 304'.",
        )

    #    - High-Cr Martensitic Stainless Steel: AiSi 410 (Shim removing Clip: Cr ~12.1%, Mn ~0.54%, Ni ~0.21%)
    if 9.0 <= cr < 14.5 and ni < 2.0 and mn < 3.0:
        return (
            "AiSi 410",
            ["AiSi 410"],
            f"~12% Cr low-Ni martensitic stainless signature (Cr={cr:.2f}%, Mn={mn:.2f}%) matches 'AiSi 410'.",
        )

    #    - Low-Alloy Cr Steels (~0.75-2.0% Cr):
    #      EN 31 (Valve Set removing Base: Cr=1.45% [1.16-1.74], Mn=0.47% [0.35-0.59], Ni=0.04%)
    #      AiSi 410 (IC Stud & NR Nut Loosening Spanner: Cr=1.03% [0.824-1.236], Mn=0.86% [0.645-1.075], Mo=0.18%)
    if 0.75 <= cr <= 2.05:
        # Guard against Cr-Ni steels (like Site 4 Ball Damage with Ni ~1.9-2.0%)
        if ni >= 0.80:
            return (
                None,
                [],
                f"Measured Ni ({ni:.2f}%) with low Cr ({cr:.2f}%) contradicts both EN 31 (Ni ~0.04%) and AiSi 410 (Ni ~0.11%).",
            )
        if cr >= 1.20 and (mn == 0.0 or mn <= 0.68):
            return (
                "EN 31",
                ["EN 31", "AiSi 410"],
                f"~1.45% Cr bearing steel signature (Cr={cr:.2f}%, Mn={mn:.2f}%) matches 'EN 31'.",
            )
        return (
            "AiSi 410",
            ["AiSi 410", "EN 31"],
            f"~1.0% Cr-Mn alloy steel signature (Cr={cr:.2f}%, Mn={mn:.2f}%) matches 'AiSi 410' / 'EN 31'.",
        )

    #    - Carbon Steel (CS):
    #      Magnet Nut Spanner (Mn=1.16% [0.928-1.392], Cr=0.05%, Ni=0.04%)
    #      Body Holding Fixture (Mn=0.71% [0.5325-0.8875], Zn=0.49%)
    #      Seal Ring remover (Mn=0.35% [0.2625-0.4375], Zn=0.30%, Fe=99%)
    if cr < 0.75 and ni < 0.50 and 0.15 <= mn <= 1.85:
        if fe > 0.0 and fe < 50.0:
            return (
                None,
                [],
                f"Iron content (Fe={fe:.2f}%) is too low for Carbon Steel (CS).",
            )
        return (
            "CS",
            ["CS"],
            f"Carbon steel signature (Mn={mn:.2f}%, low/absent Cr & Ni) matches 'CS'.",
        )

    return (
        None,
        [],
        f"Measured composition (Cr={cr:.2f}%, Ni={ni:.2f}%, Mn={mn:.2f}%) does not match any Cleaning Area indirect material family.",
    )


def _pick_best_element_measurement(
    sym: str,
    band: IndirectElementBand,
    raw_wt: Dict[str, float],
    metal_wt: Dict[str, float],
    has_light_dilution: bool,
) -> Optional[float]:
    """
    Select the measured value for element `sym`.
    If light elements (C, O, F, N) diluted the EDS spectrum, we check whether
    metal-basis wt% or raw wt% is closer to the reference value, preferring
    metal-basis wt% because `Cleaning area.xlsx` references are carbon/oxygen-free.
    """
    raw_v = raw_wt.get(sym)
    metal_v = metal_wt.get(sym)
    if raw_v is None and metal_v is None:
        return None
    if not has_light_dilution or raw_v is None or metal_v is None:
        return metal_v if metal_v is not None else raw_v

    # If either falls inside [min_value, max_value], pick the one closer to reference_value
    raw_in = band.min_value <= raw_v <= band.max_value
    metal_in = band.min_value <= metal_v <= band.max_value
    if metal_in and not raw_in:
        return metal_v
    if raw_in and not metal_in:
        return raw_v
    # Otherwise prefer metal_wt when light elements dilute the metal matrix
    return metal_v


def score_indirect_part(
    part: IndirectPartReference,
    raw_wt: Dict[str, float],
    metal_wt: Dict[str, float],
    has_light_dilution: bool,
) -> IndirectPartCandidate:
    """
    STAGE 2 — Evaluate a single IndirectPartReference against the measured EDS composition
    using the exact ±25% (<1), ±20% (1..5), ±10% (>5) tolerance rules.
    """
    within_tol: List[str] = []
    outside_tol: List[str] = []
    missing_els: List[str] = []
    contradictory_els: List[str] = []
    checks: List[IndirectElementCheck] = []

    weighted_score_sum = 0.0
    total_weight = 0.0
    major_matched_count = 0
    major_total_count = 0

    for sym, band in part.elements.items():
        ref_v = band.reference_value
        min_v = band.min_value
        max_v = band.max_value
        tol = band.tolerance

        measured_v = _pick_best_element_measurement(sym, band, raw_wt, metal_wt, has_light_dilution)

        # Special handling for explicit Fe(99%) in Seal Ring remover when user entered Fe: Bal. or steel without Fe
        if sym == "Fe" and measured_v is None:
            # If other steel elements are present and sum < 25%, Fe wasn't explicitly typed
            other_sum = sum(v for k, v in metal_wt.items() if k != "Fe")
            if 0.0 < other_sum < 30.0:
                measured_v = round(100.0 - other_sum, 4)

        # Assign element importance weight by role and reference concentration tier
        if sym == "Fe":
            # Matrix balance confirmation element (only populated on Seal Ring remover)
            weight = 1.0
        elif part.material == "CS" and sym == "Mn":
            # Mn is the primary alloying discriminator among CS parts (0.35% vs 0.71% vs 1.16%)
            weight = 4.5
            major_total_count += 1
        elif ref_v > 5.0:
            weight = 4.5
            major_total_count += 1
        elif ref_v >= 1.0:
            weight = 3.5
            major_total_count += 1
        elif ref_v >= 0.25:
            weight = 2.0
            if part.material == "CS":
                major_total_count += 1
        else:
            # Trace element (< 0.25 wt%, e.g. V 0.08%, Co 0.06%, Nb 0.02%, Pb 0.02%)
            # Often below standard EDS detection limit (~0.1-0.2 wt%).
            weight = 1.0 if measured_v is not None else 0.20

        if measured_v is None:
            missing_els.append(sym)
            # If a major element (>= 0.5%) is missing, score is 0.0;
            # if a trace XRF element (< 0.25%) is unmeasured in EDS, neutral partial score
            if ref_v >= 0.50:
                el_score = 0.0
            elif ref_v >= 0.20:
                el_score = 0.25
            else:
                el_score = 0.65

            checks.append(
                IndirectElementCheck(
                    element=sym,
                    reference_value=ref_v,
                    tolerance=tol,
                    min_value=min_v,
                    max_value=max_v,
                    measured_value=None,
                    status="missing",
                    deviation_pct=None,
                    score=el_score,
                )
            )
        else:
            dev_pct = ((measured_v - ref_v) / ref_v) * 100.0 if ref_v > 0 else 0.0
            half_band = max(1e-6, ref_v * tol)

            if min_v - 1e-6 <= measured_v <= max_v + 1e-6:
                within_tol.append(sym)
                if sym != "Fe" and (ref_v >= 0.25 or (part.material == "CS" and sym == "Mn")):
                    major_matched_count += 1
                # Score between 0.90 (at tolerance boundary) and 1.00 (at exact reference value)
                rel_pos = min(1.0, abs(measured_v - ref_v) / half_band)
                el_score = 1.0 - 0.10 * rel_pos
                status_str = "within_tolerance"
            else:
                outside_tol.append(sym)
                excess = (min_v - measured_v) if measured_v < min_v else (measured_v - max_v)
                rel_miss = excess / half_band
                el_score = max(0.0, 0.72 * math.exp(-0.90 * (rel_miss ** 2)))
                status_str = "outside_tolerance"

                # Flag severe overshoot on low/trace reference elements or CS Mn mismatch as contradictory
                if ref_v <= 0.25 and measured_v >= max(1.0, ref_v * 5.0):
                    contradictory_els.append(f"{sym} ({measured_v:.2f}% vs ref {ref_v:.2f}%)")
                elif part.material == "CS" and sym == "Mn" and rel_miss > 2.5:
                    contradictory_els.append(f"Mn ({measured_v:.2f}% vs ref {ref_v:.2f}%)")

            checks.append(
                IndirectElementCheck(
                    element=sym,
                    reference_value=ref_v,
                    tolerance=tol,
                    min_value=min_v,
                    max_value=max_v,
                    measured_value=measured_v,
                    status=status_str,
                    deviation_pct=dev_pct,
                    score=el_score,
                )
            )

        weighted_score_sum += weight * el_score
        total_weight += weight

    # Check for contradictory foreign alloy elements present in the measured spectrum
    # that are NOT in the part's reference elements at all
    for m_sym, m_val in metal_wt.items():
        if m_sym in LIGHT_AND_SURFACE_ELEMENTS or m_sym == "Fe":
            continue
        if m_sym in part.elements:
            continue
        # Allow normal steel Si residual (<= 1.0%) without penalty
        if m_sym == "Si" and m_val <= 1.0:
            continue
        # Allow minor surface Zn (< 0.8%) on CS/steel parts without hard contradiction,
        # but penalize if Zn >= 0.35% on a CS part that does not have Zn (e.g. Magnet Nut Spanner vs Body Holding Fixture)
        if m_sym == "Zn":
            if part.material == "CS" and m_val >= 0.25:
                contradictory_els.append(f"Zn ({m_val:.2f}% not in {part.part_name} ref)")
            elif m_val >= 1.0:
                contradictory_els.append(f"Zn ({m_val:.2f}%)")
            continue
        if m_val >= 0.60:
            contradictory_els.append(f"{m_sym} ({m_val:.2f}%)")

    base_compat = (weighted_score_sum / total_weight) if total_weight > 0 else 0.0

    # Apply penalty for contradictory elements
    if contradictory_els:
        base_compat *= (0.60 ** len(contradictory_els))

    # If none of the major elements matched within tolerance and base_compat is mediocre, cap it
    if major_total_count > 0 and major_matched_count == 0:
        base_compat = min(base_compat, 0.58)

    compat_clamped = max(0.0, min(1.0, base_compat))
    compat_pct = int(round(compat_clamped * 100))

    # Build human-readable summary note
    note_parts: List[str] = []
    if within_tol:
        note_parts.append(f"Within tolerance: {', '.join(within_tol)}")
    if outside_tol:
        note_parts.append(f"Outside tolerance: {', '.join(outside_tol)}")
    if contradictory_els:
        note_parts.append(f"Contradictory: {', '.join(contradictory_els)}")
    if not note_parts:
        note_parts.append("No matching reference elements.")

    return IndirectPartCandidate(
        sn=part.sn,
        part_name=part.part_name,
        location=part.location,
        material=part.material,
        compatibility=compat_clamped,
        compatibility_pct=compat_pct,
        within_tolerance_elements=within_tol,
        outside_tolerance_elements=outside_tol,
        missing_elements=missing_els,
        contradictory_elements=contradictory_els,
        element_checks=checks,
        notes=" • ".join(note_parts),
    )


def predict_indirect_source(
    composition: Dict[str, Any],
    max_candidates: int = 6,
) -> Dict[str, Any]:
    """
    Execute the two-stage Indirect Material Source Rule Engine on a single EDS spectrum.

    Stage 1: EDS Elemental Composition -> Indirect Material Family
    Stage 2: Indirect Material Family -> Probable Indirect Source / Part Name
    """
    raw_wt, metal_wt, has_light_dilution = _prepare_dual_basis_composition(composition)

    primary_family, candidate_families, stage1_reason = classify_indirect_material_family(
        raw_wt, metal_wt
    )

    if not primary_family or not candidate_families:
        return {
            "decision": "unknown",
            "statusLabel": "Unknown / Inconclusive",
            "indirectFamily": "Unknown / Inconclusive",
            "indirectFamilyLabel": "No Matching Indirect Material Family",
            "stage1Reason": stage1_reason,
            "topIndirectSource": None,
            "candidates": [],
            "evaluatedPartsCount": 0,
            "toleranceRules": [
                {"range": "< 1 wt%", "tolerance": "±25%"},
                {"range": "1 to 5 wt%", "tolerance": "±20%"},
                {"range": "> 5 wt%", "tolerance": "±10%"},
            ],
        }

    all_parts = load_indirect_reference()
    # Stage 2: Filter strictly to parts belonging to the Stage 1 candidate material family(ies)
    family_parts = [p for p in all_parts if p.material in candidate_families]

    scored: List[IndirectPartCandidate] = [
        score_indirect_part(p, raw_wt, metal_wt, has_light_dilution)
        for p in family_parts
    ]

    # Sort by:
    #  1. compatibility descending
    #  2. number of within-tolerance elements descending
    #  3. primary_family match first
    scored.sort(
        key=lambda c: (
            round(c.compatibility, 4),
            len(c.within_tolerance_elements),
            1 if c.material == primary_family else 0,
        ),
        reverse=True,
    )

    # Filter out implausible candidates (< 40% compatibility)
    viable = [c for c in scored if c.compatibility_pct >= 40]

    if not viable or viable[0].compatibility_pct < 48:
        best_attempt = scored[0].to_dict() if scored else None
        return {
            "decision": "unknown",
            "statusLabel": "Unknown / Inconclusive",
            "indirectFamily": primary_family,
            "indirectFamilyLabel": INDIRECT_FAMILY_LABELS.get(primary_family, primary_family),
            "stage1Reason": (
                f"{stage1_reason} However, measured element concentrations fall outside the acceptable "
                f"tolerance bands of all {primary_family} indirect sources."
            ),
            "topIndirectSource": None,
            "bestOutOfToleranceAttempt": best_attempt,
            "candidates": [c.to_dict() for c in scored[:3]],
            "evaluatedPartsCount": len(family_parts),
            "toleranceRules": [
                {"range": "< 1 wt%", "tolerance": "±25%"},
                {"range": "1 to 5 wt%", "tolerance": "±20%"},
                {"range": "> 5 wt%", "tolerance": "±10%"},
            ],
        }

    top = viable[0]
    runner_up = viable[1] if len(viable) > 1 else None
    margin_pct = (top.compatibility_pct - runner_up.compatibility_pct) if runner_up else 100

    # Update indirectFamily to match the winning part's exact classification if from a boundary family
    winning_family = top.material

    if top.compatibility_pct >= 72 and margin_pct >= 6:
        decision = "identified"
        status_label = "Identified Indirect Source"
    else:
        decision = "ambiguous"
        status_label = "Multiple Plausible Indirect Sources"

    return {
        "decision": decision,
        "statusLabel": status_label,
        "indirectFamily": winning_family,
        "indirectFamilyLabel": INDIRECT_FAMILY_LABELS.get(winning_family, winning_family),
        "stage1Reason": stage1_reason,
        "topIndirectSource": top.to_dict(),
        "candidates": [c.to_dict() for c in viable[:max_candidates]],
        "evaluatedPartsCount": len(family_parts),
        "toleranceRules": [
            {"range": "< 1 wt%", "tolerance": "±25%"},
            {"range": "1 to 5 wt%", "tolerance": "±20%"},
            {"range": "> 5 wt%", "tolerance": "±10%"},
        ],
    }


def predict_indirect_particle(
    spectra: List[Dict[str, Any]],
    max_candidates: int = 6,
) -> Dict[str, Any]:
    """
    Run the Indirect Material Source Rule Engine on a pooled particle (mean of spectra).
    """
    if not spectra:
        return predict_indirect_source({}, max_candidates=max_candidates)
    if len(spectra) == 1:
        return predict_indirect_source(spectra[0], max_candidates=max_candidates)

    # Compute mean composition across spectra for the pooled particle summary
    elem_sums: Dict[str, float] = {}
    elem_counts: Dict[str, int] = {}
    for s in spectra:
        _, metal_s, _ = _prepare_dual_basis_composition(s)
        for k, v in metal_s.items():
            elem_sums[k] = elem_sums.get(k, 0.0) + v
            elem_counts[k] = elem_counts.get(k, 0) + 1

    pooled_comp = {
        k: round(elem_sums[k] / elem_counts[k], 4)
        for k in elem_sums
        if elem_counts.get(k, 0) > 0
    }
    return predict_indirect_source(pooled_comp, max_candidates=max_candidates)
