"""Three-tier Rule Engine (Phase 3 & Section 11).

Separates:
  1. Category A (DOMAIN): Engineering/metallurgical domain rules (not tuned on dataset).
  2. Category B (STATISTICAL): Data-derived statistical ranges from Level 1 validated reference spectra.
  3. Category C (ML): Probabilistic family & partial-label candidate compatibility evidence.

Supports required elements, forbidden/contradictory elements, concentration ranges,
element ratios, chemistry/family compatibility, surface/coating effects, location context,
uncertainty/tolerance (sigma-model), missing elements (NOT_REPORTED = neutral), and
multi-candidate rules.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from isp.aggregation import SiteAggregate, sigma_eds
from isp.registry import COMPONENT_BY_ID, INDISTINGUISHABILITY_GROUPS


@dataclass(frozen=True)
class DomainFamilyRule:
    family_id: str
    label: str
    required_elements: Tuple[str, ...]
    forbidden_elements: Dict[str, float]  # element -> max allowed wt% on metal basis
    metal_bands: Dict[str, Tuple[float, float]]  # element -> (min_wt%, max_wt%) on metal basis
    ratio_bands: Dict[str, Tuple[float, float]]  # ratio -> (min, max)
    surface_override: Optional[str] = None


# Category A: Engineering / metallurgical domain specifications (standard DIN/EN/ISO alloy envelopes)
DOMAIN_FAMILY_RULES: Dict[str, DomainFamilyRule] = {
    "PURE_IRON_SOFT_MAGNETIC": DomainFamilyRule(
        family_id="PURE_IRON_SOFT_MAGNETIC",
        label="Soft Magnetic Pure Iron",
        required_elements=("Fe",),
        forbidden_elements={"Cr": 0.45, "Ni": 0.5, "Cu": 1.0, "Zn": 2.0, "W": 0.5, "Mo": 0.5},
        metal_bands={"Fe": (98.5, 100.0), "Mn": (0.0, 0.45), "Si": (0.0, 0.5)},
        ratio_bands={},
    ),
    "PLAIN_C_STEEL": DomainFamilyRule(
        family_id="PLAIN_C_STEEL",
        label="Plain Carbon / Low-Alloy Steel",
        required_elements=("Fe",),
        forbidden_elements={"Cr": 0.8, "Ni": 1.0, "Cu": 2.0, "W": 0.5, "Mo": 0.5},
        metal_bands={"Fe": (96.0, 99.6), "Mn": (0.25, 1.25), "Si": (0.0, 0.8), "Cr": (0.0, 0.5)},
        ratio_bands={"Cr/Fe": (0.0, 0.006)},
    ),
    "LEADED_PLAIN_C": DomainFamilyRule(
        family_id="LEADED_PLAIN_C",
        label="Leaded Plain Carbon Steel",
        required_elements=("Fe",),
        forbidden_elements={"Cr": 1.0, "Ni": 1.0, "W": 0.5},
        metal_bands={"Fe": (95.5, 99.5), "Mn": (0.3, 1.3), "Pb": (0.05, 0.6)},
        ratio_bands={},
    ),
    "MN_CR_MN_STEEL": DomainFamilyRule(
        family_id="MN_CR_MN_STEEL",
        label="Mn / Cr-Mn Steel (1.2-1.5 Mn)",
        required_elements=("Fe", "Mn"),
        forbidden_elements={"Ni": 1.5, "Cu": 2.0, "W": 0.5},
        metal_bands={"Fe": (95.0, 99.0), "Mn": (0.95, 2.2), "Cr": (0.0, 1.4)},
        ratio_bands={"Mn/Fe": (0.009, 0.025)},
    ),
    "FREE_CUTTING_RESULPH_ETG": DomainFamilyRule(
        family_id="FREE_CUTTING_RESULPH_ETG",
        label="Resulphurised / ETG100 Steel",
        required_elements=("Fe", "Mn"),
        forbidden_elements={"Cr": 1.0, "Ni": 1.0, "W": 0.5},
        metal_bands={"Fe": (95.5, 99.2), "Mn": (1.0, 2.0), "Si": (0.1, 0.8), "S": (0.0, 0.6)},
        ratio_bands={"Mn/Fe": (0.010, 0.022)},
    ),
    "BEARING_100CR6": DomainFamilyRule(
        family_id="BEARING_100CR6",
        label="100Cr6 Bearing Steel (Sl2 B1)",
        required_elements=("Fe", "Cr"),
        forbidden_elements={"Ni": 1.5, "Cu": 1.5, "W": 0.5, "Zn": 2.0},
        metal_bands={"Fe": (96.0, 98.8), "Cr": (1.15, 2.2), "Mn": (0.15, 0.7), "Si": (0.1, 0.6)},
        ratio_bands={"Cr/Fe": (0.011, 0.024)},
    ),
    "SPRING_CR_SI_STEEL": DomainFamilyRule(
        family_id="SPRING_CR_SI_STEEL",
        label="Si-Cr Spring Steel (VDSiCrDIN)",
        required_elements=("Fe", "Si", "Cr"),
        forbidden_elements={"Ni": 1.5, "W": 0.5, "Cu": 1.5},
        metal_bands={"Fe": (95.0, 98.5), "Si": (1.05, 2.6), "Cr": (0.4, 1.2), "Mn": (0.3, 1.1)},
        ratio_bands={"Si/Mn": (1.2, 6.0)},
    ),
    "HSS_TOOL_STEEL": DomainFamilyRule(
        family_id="HSS_TOOL_STEEL",
        label="High-Speed Tool Steel (Sl2b17 / Sl4b2 / M2)",
        required_elements=("Fe", "Cr", "W", "Mo", "V"),
        forbidden_elements={"Cu": 2.0, "Zn": 2.0},
        metal_bands={"Fe": (74.0, 86.0), "Cr": (3.5, 5.8), "W": (5.0, 10.5), "Mo": (3.2, 7.0), "V": (1.5, 3.5)},
        ratio_bands={},
    ),
    "SL48_NOZZLE_STEEL": DomainFamilyRule(
        family_id="SL48_NOZZLE_STEEL",
        label="Sl48 Case-Hardening Nozzle Steel",
        required_elements=("Fe",),
        forbidden_elements={"Cu": 2.0, "Zn": 2.0, "W": 1.0},
        metal_bands={"Fe": (94.0, 99.0), "Cr": (0.3, 2.0), "Ni": (0.0, 2.5)},
        ratio_bands={},
    ),
    "AUSTENITIC_SS": DomainFamilyRule(
        family_id="AUSTENITIC_SS",
        label="Stainless Steel (SS 302/304/316)",
        required_elements=("Fe", "Cr", "Ni"),
        forbidden_elements={"Cu": 3.0, "Zn": 2.0, "W": 1.0},
        metal_bands={"Fe": (62.0, 78.0), "Cr": (16.0, 22.0), "Ni": (7.0, 15.0), "Mn": (0.5, 2.8)},
        ratio_bands={"Ni/Cr": (0.35, 0.85)},
    ),
    "CU_SN_BRONZE": DomainFamilyRule(
        family_id="CU_SN_BRONZE",
        label="Cu / Cu-Sn Bronze / Brass",
        required_elements=("Cu",),
        forbidden_elements={"Cr": 3.0, "W": 1.0},
        metal_bands={"Cu": (50.0, 100.0), "Sn": (0.0, 15.0)},
        ratio_bands={},
    ),
    "NI_ALLOY_PLATING": DomainFamilyRule(
        family_id="NI_ALLOY_PLATING",
        label="Nickel Alloy / Ni Plating",
        required_elements=("Ni",),
        forbidden_elements={"Cu": 5.0, "Zn": 5.0},
        metal_bands={"Ni": (70.0, 100.0), "Fe": (0.0, 20.0), "Cr": (0.0, 8.0)},
        ratio_bands={},
        surface_override="Ni",
    ),
    "ZN_FLAKES_PLATING": DomainFamilyRule(
        family_id="ZN_FLAKES_PLATING",
        label="Zinc Flake / Zn Phosphate / Zn Plating",
        required_elements=("Zn",),
        forbidden_elements={"Cu": 5.0, "W": 1.0, "Ni": 5.0},
        metal_bands={"Zn": (15.0, 100.0), "Fe": (0.0, 85.0)},
        ratio_bands={},
        surface_override="Zn",
    ),
}


@dataclass
class RuleEvidenceItem:
    rule_id: str
    category: str  # DOMAIN, STATISTICAL, ML
    outcome: str   # SUPPORT, CONTRADICT, NEUTRAL, VETO
    score_delta: float
    supporting_elements: List[str] = field(default_factory=list)
    contradicting_elements: List[str] = field(default_factory=list)
    reason: str = ""


def evaluate_domain_family(
    site: SiteAggregate,
    family_id: str,
    coating_state: str = "UNKNOWN",
    coating_type: Optional[str] = None,
) -> RuleEvidenceItem:
    """Evaluate Category A domain rules for a material family against a site aggregate."""
    rule = DOMAIN_FAMILY_RULES.get(family_id)
    if not rule or not site.metal_basis:
        return RuleEvidenceItem(
            rule_id=f"DOM_FAM_{family_id}",
            category="DOMAIN",
            outcome="NEUTRAL",
            score_delta=0.0,
            reason="No spectrum metal-basis or domain rule available.",
        )

    mb = dict(site.metal_basis)
    # Surface coating compensation: if ZnP or Zn coating is present and we evaluate a bulk steel family,
    # renormalize the non-Zn/P metallic elements so Zn from coating does not falsely veto bulk steel.
    coating_explained = False
    if family_id not in ("ZN_FLAKES_PLATING",) and (
        coating_type in ("ZnP", "Zn") or ("Zn" in mb and "Fe" in mb and mb["Fe"] >= 45.0)
    ):
        non_zn = {k: v for k, v in mb.items() if k not in ("Zn", "P")}
        s_nz = sum(non_zn.values())
        if s_nz > 10.0 and "Zn" in mb:
            mb = {k: round(v * 100.0 / s_nz, 4) for k, v in non_zn.items()}
            coating_explained = True

    sup: List[str] = []
    con: List[str] = []
    veto = False
    score = 0.0

    # 1. Check required elements (only if metallic spectrum has data)
    for req in rule.required_elements:
        val = mb.get(req, 0.0)
        if val > 0.05:
            sup.append(req)
            score += 0.25
        else:
            con.append(req)
            # Missing required major alloying element in a measured metallic spectrum is a strong contradiction
            if req in ("Cu", "Ni", "Zn", "W", "Cr") and len(mb) >= 1:
                if req == "Cr" and family_id in ("BEARING_100CR6", "SPRING_CR_SI_STEEL"):
                    score -= 1.2
                else:
                    veto = True
                    score -= 2.5

    # 2. Check forbidden elements (Category A physical vetoes)
    for fel, max_ok in rule.forbidden_elements.items():
        val = mb.get(fel, 0.0)
        sig = site.metal_basis_sigma.get(fel, sigma_eds(val, fel))
        if val > max_ok + 2.0 * sig:
            con.append(fel)
            if val > max_ok + 5.0 * sig and val > 3.0:
                veto = True
                score -= 2.5
            else:
                score -= 1.0

    # 3. Check concentration bands with sigma tolerance
    for el, (lo, hi) in rule.metal_bands.items():
        if el not in mb:
            if lo > 0.5:
                con.append(el)
                score -= 0.6
            continue
        val = mb[el]
        sig = site.metal_basis_sigma.get(el, sigma_eds(val, el))
        if lo - 2.0 * sig <= val <= hi + 2.0 * sig:
            if el not in sup:
                sup.append(el)
            score += 0.35
        else:
            dist = (lo - val) / max(0.1, sig) if val < lo else (val - hi) / max(0.1, sig)
            if dist > 3.5:
                if el not in con:
                    con.append(el)
                score -= min(1.5, 0.25 * dist)

    if coating_explained:
        sup.append("Zn (explained by surface coating)")

    outcome = "VETO" if veto else ("SUPPORT" if score > 0.2 and not con else "CONTRADICT" if score < -0.3 else "NEUTRAL")
    return RuleEvidenceItem(
        rule_id=f"DOM_FAM_{family_id}",
        category="DOMAIN",
        outcome=outcome,
        score_delta=round(score, 4),
        supporting_elements=sup,
        contradicting_elements=con,
        reason=f"Domain check for {rule.label}: {outcome} (score={score:+.2f})",
    )


def evaluate_component_domain_rules(
    site: SiteAggregate,
    component_id: str,
    inferred_family_id: Optional[str],
    analyst_family_id: Optional[str],
    coating_state: str,
    coating_type: Optional[str],
) -> List[RuleEvidenceItem]:
    """Evaluate Category A domain rules for a candidate component."""
    spec = COMPONENT_BY_ID.get(component_id)
    if not spec:
        return []
    ev: List[RuleEvidenceItem] = []

    # Rule 1: Chemistry / material-family compatibility
    ref_fam = analyst_family_id or inferred_family_id
    if ref_fam:
        if ref_fam in spec.compatible_families:
            ev.append(RuleEvidenceItem(
                rule_id=f"DOM_COMP_FAM_{component_id}",
                category="DOMAIN",
                outcome="SUPPORT",
                score_delta=0.8,
                reason=f"Component {spec.canonical_name} is compatible with material family {ref_fam}.",
            ))
        else:
            ev.append(RuleEvidenceItem(
                rule_id=f"DOM_COMP_FAM_{component_id}",
                category="DOMAIN",
                outcome="CONTRADICT",
                score_delta=-1.4,
                reason=f"Component {spec.canonical_name} expects {spec.compatible_families}, but family is {ref_fam}.",
            ))

    # Rule 2: Surface / coating compatibility
    if coating_state in ("COATED", "TRACES") and coating_type:
        if coating_type in spec.expected_coatings:
            ev.append(RuleEvidenceItem(
                rule_id=f"DOM_COMP_COAT_{component_id}",
                category="DOMAIN",
                outcome="SUPPORT",
                score_delta=0.45,
                supporting_elements=[coating_type],
                reason=f"Surface coating {coating_type} matches expected treatment on {spec.canonical_name}.",
            ))
        elif component_id == "MAGNET_CORE" and coating_type in ("ZnP", "Zn"):
            ev.append(RuleEvidenceItem(
                rule_id=f"DOM_COMP_COAT_{component_id}",
                category="DOMAIN",
                outcome="CONTRADICT",
                score_delta=-0.9,
                contradicting_elements=[coating_type],
                reason="Magnet Core is uncoated soft iron; ZnP/Zn coating contradicts Magnet Core.",
            ))

    # Rule 3: Spectrum-level domain checks across the component's compatible families
    if site.metal_basis:
        fam_evals = [evaluate_domain_family(site, f, coating_state, coating_type) for f in spec.compatible_families]
        if fam_evals:
            best = max(fam_evals, key=lambda x: x.score_delta)
            ev.append(best)

    return ev
