"""
rule_engine/component_scoring.py
================================
Component-level scoring engine. Scores how well a new EDS spectrum matches each
candidate component's historical fingerprint.

Stdlib only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

from rule_engine.normalize import NormalizedSpectrum
from rule_engine.scoring import get_knowledge_base

# We assume component_fingerprints is available as described
try:
    from rule_engine.component_fingerprints import ComponentFingerprint, load_fingerprints
except ImportError:
    # Dummy definition for type hinting if not yet implemented
    @dataclass
    class ComponentFingerprint:
        component_id: str
        display_name: str
        family_ids: List[str]
        elements: Dict[str, Any]
        ratios: Dict[str, Any]
        sample_count: int
        quality: str

    def load_fingerprints() -> Dict[str, ComponentFingerprint]:
        return {}


@dataclass
class ComponentScore:
    component_id: str
    display_name: str
    compatibility: float  # 0.0 to 1.0
    family_ids: List[str]
    sample_count: int
    fingerprint_quality: str  # LOW, MEDIUM, HIGH
    element_distances: Dict[str, float]  # per-element z-scores
    matched_elements: List[str]
    missing_elements: List[str]
    ratio_matches: Dict[str, bool]
    evidence_sufficiency: float  # fraction of expected elements measured
    decision: str = ""  # identified, ambiguous, insufficient_data


def score_component(
    spectrum: NormalizedSpectrum,
    fingerprint: ComponentFingerprint,
) -> ComponentScore:
    """Score how well a spectrum matches a component fingerprint."""
    
    kb = get_knowledge_base()
    discriminators = set()
    for f_id in fingerprint.family_ids:
        fam = kb.families.get(f_id, {})
        discriminators.update(fam.get("discriminators", []))
        
    expected_elements = [e for e, stat in fingerprint.elements.items() if stat.role == 'expected']
    
    matched_elements = []
    missing_elements = []
    foreign_elements = []
    element_distances = {}
    
    z_squared_sum = 0.0
    weight_sum = 0.0

    # 1. Standardized element distance and weighting
    for element, stat in fingerprint.elements.items():
        if spectrum.is_measured(element):
            val = spectrum.metal(element) or 0.0
            matched_elements.append(element)
            
            # calculate z
            if stat.iqr > 0:
                z = (val - stat.median) / stat.iqr
            elif stat.iqr == 0 and stat.std > 0:
                z = (val - stat.median) / stat.std
            else:
                z = abs(val - stat.median) / max(0.1, stat.median * 0.05)
                
            z = min(abs(z), 5.0)  # cap |z| at 5.0
            
            if val > stat.median:
                element_distances[element] = z
            else:
                element_distances[element] = -z
                
            # determine weight
            if stat.role == 'expected':
                w = 2.0
            elif stat.role == 'common':
                w = 1.0
            else:
                w = 0.3
                
            if element in discriminators:
                w *= 2.0
                
            if element in ('Fe', 'Cu', 'Ni'):
                w = min(w, 0.5)
                
            z_squared_sum += w * (z ** 2)
            weight_sum += w
            
        elif stat.role == 'expected':
            missing_elements.append(element)
            
    # Foreign elements check
    for element in spectrum.alloy_elements():
        if element not in fingerprint.elements:
            val = spectrum.metal(element) or 0.0
            if val > 2.0:
                foreign_elements.append(element)

    # 4. Ratio compatibility
    ratio_matches = {}
    if hasattr(fingerprint, 'ratios'):
        for r_name, r_stat in fingerprint.ratios.items():
            if "/" in r_name:
                a, b = r_name.split("/")
                a = a.strip()
                b = b.strip()
                ratio_val = spectrum.ratio(a, b)
                if ratio_val is not None:
                    val, _ = ratio_val
                    q1 = getattr(r_stat, 'q1', 0.0)
                    q3 = getattr(r_stat, 'q3', 0.0)
                    r_min = getattr(r_stat, 'min', 0.0)
                    r_max = getattr(r_stat, 'max', 0.0)
                    
                    if q1 <= val <= q3:
                        ratio_matches[r_name] = True
                    elif r_min <= val <= r_max:
                        ratio_matches[r_name] = True
                    else:
                        ratio_matches[r_name] = False

    # 5. Composite compatibility score
    weighted_mean_z2 = z_squared_sum / weight_sum if weight_sum > 0 else 0.0
    fit = math.exp(-0.5 * weighted_mean_z2)
    
    n_expected = len(expected_elements)
    n_matched_expected = sum(1 for e in expected_elements if e in matched_elements)
    
    evidence = n_matched_expected / n_expected if n_expected > 0 else 1.0
    
    n_missing_expected = len(missing_elements)
    n_foreign = len(foreign_elements)
    
    presence_penalty = 1.0 - 0.1 * n_missing_expected - 0.05 * n_foreign
    
    compatibility = min(0.95, fit * evidence * max(0.1, presence_penalty))
    
    # 6. Fingerprint quality adjustment
    quality = getattr(fingerprint, 'quality', 'HIGH').upper()
    if quality == 'MEDIUM':
        # Widen acceptable z range by 1.5x -> z / 1.5 -> (z/1.5)^2 = z^2 / 2.25
        # So we can adjust fit
        weighted_mean_z2_adj = weighted_mean_z2 / (1.5 ** 2)
        fit = math.exp(-0.5 * weighted_mean_z2_adj)
        compatibility = min(0.95, fit * evidence * max(0.1, presence_penalty))
    elif quality == 'LOW':
        weighted_mean_z2_adj = weighted_mean_z2 / (2.0 ** 2)
        fit = math.exp(-0.5 * weighted_mean_z2_adj)
        compatibility = min(0.7, fit * evidence * max(0.1, presence_penalty))

    return ComponentScore(
        component_id=fingerprint.component_id,
        display_name=fingerprint.display_name,
        compatibility=compatibility,
        family_ids=fingerprint.family_ids,
        sample_count=fingerprint.sample_count,
        fingerprint_quality=quality,
        element_distances=element_distances,
        matched_elements=matched_elements,
        missing_elements=missing_elements,
        ratio_matches=ratio_matches,
        evidence_sufficiency=evidence,
        decision=""
    )


def rank_components(
    spectrum: NormalizedSpectrum,
    candidate_family_ids: List[str],
    top_n: int = 10,
) -> List[ComponentScore]:
    """Rank components by their fingerprint match to the spectrum."""
    fingerprints = load_fingerprints()
    
    scored = []
    for fp in fingerprints.values():
        # Check if component belongs to any of the candidate families
        if any(f_id in candidate_family_ids for f_id in fp.family_ids):
            score = score_component(spectrum, fp)
            scored.append(score)
            
    scored.sort(key=lambda x: x.compatibility, reverse=True)
    return scored[:top_n]


def decide_component(
    ranked: List[ComponentScore],
    min_compatibility: float = 0.3,
    min_margin: float = 0.10,
) -> Tuple[str, Optional[ComponentScore]]:
    """Returns (decision_str, top_component_or_None)"""
    if not ranked:
        return "unknown", None
        
    top = ranked[0]
    
    if top.compatibility < min_compatibility:
        top.decision = "unknown"
        return "unknown", top
        
    runner_up = ranked[1] if len(ranked) > 1 else None
    
    if runner_up:
        margin = top.compatibility - runner_up.compatibility
        if margin >= min_margin:
            # Check for low quality + insufficient data
            if top.fingerprint_quality == "LOW" and top.compatibility < 0.6:
                top.decision = "insufficient_data"
                return "insufficient_data", top
            top.decision = "identified"
            return "identified", top
        else:
            top.decision = "ambiguous"
            return "ambiguous", top
    else:
        if top.fingerprint_quality == "LOW" and top.compatibility < 0.6:
            top.decision = "insufficient_data"
            return "insufficient_data", top
        top.decision = "identified"
        return "identified", top

