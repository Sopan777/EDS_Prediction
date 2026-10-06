"""Unified Candidate Scoring and Partial-Label Prediction Engine (Phase 5 & Phase 6, Sections 12-15 & 19).

Evaluates all evidence channels in a unified decision system:
  - Material-family compatibility (inferred from spectrum + analyst chemistry if provided)
  - Component fingerprint similarity (robust median/MAD distance, element presence/absence, ratios)
  - Three-tier Rule Engine (Domain, Statistical, ML)
  - Surface / coating evidence (with base-metal vs coating decoupling)
  - Particle location context (smoothed, capped, and guarded against name-leakage)
  - Partial-label EM candidate-set prior & compatibility
  - Spectrum variability & quality assessment
  - Historical reference support & epistemic uncertainty

Outputs:
  - HIGH_CONFIDENCE (IDENTIFIED): Single component when evidence uniquely distinguishes it
  - AMBIGUOUS: Ranked compatible candidates + named indistinguishability group
  - UNKNOWN (INSUFFICIENT): Refuses prediction when evidence is insufficient or external/out-of-scope
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set, Tuple
import math
import re

from isp.aggregation import SiteAggregate, aggregate_site_spectra, sigma_eds
from isp.decode import DecodedSpectrum, decode_row, NON_ALLOY_LIGHT_ELEMENTS
from isp.registry import (
    COMPONENT_BY_ID,
    INDISTINGUISHABILITY_GROUPS,
    INTERNAL_COMPONENTS,
    MATERIAL_FAMILIES,
    map_chemistry_to_family,
    map_location_zone,
    normalize_coating,
)
from isp.rules import (
    DOMAIN_FAMILY_RULES,
    RuleEvidenceItem,
    evaluate_component_domain_rules,
    evaluate_domain_family,
)
from isp.verification import ComponentReferenceFingerprint


@dataclass
class CandidatePrediction:
    component_id: str
    component_name: str
    probability: float
    compatibility_score: float
    family_compatibility: float
    fingerprint_similarity: Optional[float]
    rule_score: float
    coating_score: float
    location_score: float
    historical_reports: int
    historical_sites: int
    trust_level: int
    supporting_elements: List[str] = field(default_factory=list)
    contradicting_elements: List[str] = field(default_factory=list)
    rule_reasons: List[str] = field(default_factory=list)
    indistinguishability_group: Optional[str] = None


@dataclass
class UnifiedPredictionResult:
    prediction_status: str  # HIGH_CONFIDENCE | AMBIGUOUS | UNKNOWN
    predicted_component: Optional[str]
    predicted_component_id: Optional[str]
    confidence: float
    material_family: Dict[str, object]
    candidates: List[CandidatePrediction]
    indistinguishability_group: Optional[Dict[str, object]]
    supporting_elements: List[str]
    contradicting_elements: List[str]
    spectrum_quality: Dict[str, object]
    location_evidence: Dict[str, object]
    surface_coating_evidence: Dict[str, object]
    unknown_probability: float
    explanation: str
    model_metadata: Dict[str, object]


class UnifiedISPEngine:
    """Partial-label statistical + rule + fingerprint unified scoring engine."""

    def __init__(
        self,
        fingerprints: Dict[str, ComponentReferenceFingerprint],
        family_comp_counts: Dict[str, Dict[str, float]],
        coating_comp_counts: Dict[str, Dict[str, float]],
        zone_comp_counts: Dict[str, Dict[str, float]],
        comp_report_counts: Dict[str, int],
        comp_site_counts: Dict[str, int],
        cooccurrence_sets: Dict[str, Set[str]],
        calibrated_reports: int = 150,
        data_release: str = "r2.0-validated",
    ) -> None:
        self.fingerprints = fingerprints
        self.family_comp_counts = family_comp_counts
        self.coating_comp_counts = coating_comp_counts
        self.zone_comp_counts = zone_comp_counts
        self.comp_report_counts = comp_report_counts
        self.comp_site_counts = comp_site_counts
        self.cooccurrence_sets = cooccurrence_sets
        self.calibrated_reports = calibrated_reports
        self.data_release = data_release

    @classmethod
    def fit_from_trusted_sites(
        cls,
        sites: List[SiteAggregate],
        site_meta: Dict[str, Dict[str, object]],
        site_candidates: Dict[str, List[str]],
        fingerprints: Dict[str, ComponentReferenceFingerprint],
        data_release: str = "r2.0-validated",
    ) -> "UnifiedISPEngine":
        """Fit partial-label EM compatibility tables on training sites (grouped by report)."""
        comp_ids = [c.component_id for c in INTERNAL_COMPONENTS]
        # Initialize uniform weights w_{i, c} = 1 / |C_i| for c in C_i, then run 5 iterations of Partial-Label EM
        weights: Dict[str, Dict[str, float]] = {}
        for suid, cands in site_candidates.items():
            if not cands:
                continue
            w0 = 1.0 / len(cands)
            weights[suid] = {c: w0 for c in cands}

        for _ in range(5):
            fam_counts: Dict[str, Dict[str, float]] = {}
            coat_counts: Dict[str, Dict[str, float]] = {}
            zone_counts: Dict[str, Dict[str, float]] = {}
            for suid, cw in weights.items():
                meta = site_meta.get(suid, {})
                fam = meta.get("family_id")
                coat = meta.get("coating_type") or meta.get("coating_state", "UNKNOWN")
                zone = meta.get("location_zone", "UNKNOWN_ZONE")
                leak = bool(meta.get("location_leak", False))
                for cid, w in cw.items():
                    if fam:
                        fam_counts.setdefault(fam, {})[cid] = fam_counts.get(fam, {}).get(cid, 0.0) + w
                    if coat:
                        coat_counts.setdefault(coat, {})[cid] = coat_counts.get(coat, {}).get(cid, 0.0) + w
                    if zone and not leak and zone != "UNKNOWN_ZONE":
                        zone_counts.setdefault(zone, {})[cid] = zone_counts.get(zone, {}).get(cid, 0.0) + w

            # E-step: re-estimate w_{i, c} proportional to P(c | fam) * P(c | coat)
            for suid, cw in weights.items():
                if len(cw) <= 1:
                    continue
                meta = site_meta.get(suid, {})
                fam = meta.get("family_id")
                coat = meta.get("coating_type") or meta.get("coating_state", "UNKNOWN")
                new_w: Dict[str, float] = {}
                for cid in cw:
                    f_sc = (fam_counts.get(fam, {}).get(cid, 0.0) + 0.5) if fam else 1.0
                    c_sc = (coat_counts.get(coat, {}).get(cid, 0.0) + 0.5) if coat else 1.0
                    # Do not let single-candidate frequency break physical symmetry inside multi-candidate sets
                    new_w[cid] = math.sqrt(f_sc * c_sc)
                s_w = sum(new_w.values())
                if s_w > 0:
                    weights[suid] = {cid: v / s_w for cid, v in new_w.items()}

        # Compute report-level and site-level support counts and co-occurrence sets
        rep_by_comp: Dict[str, Set[str]] = {c: set() for c in comp_ids}
        site_by_comp: Dict[str, int] = {c: 0 for c in comp_ids}
        cooccur: Dict[str, Set[str]] = {c: set() for c in comp_ids}
        all_reports: Set[str] = set()
        for suid, cands in site_candidates.items():
            if not cands:
                continue
            rep_id = str(site_meta.get(suid, {}).get("report_id", suid))
            all_reports.add(rep_id)
            for cid in cands:
                if cid in rep_by_comp:
                    rep_by_comp[cid].add(rep_id)
                    site_by_comp[cid] += 1
                    for other in cands:
                        if other != cid:
                            cooccur[cid].add(other)

        return cls(
            fingerprints=fingerprints,
            family_comp_counts=fam_counts,
            coating_comp_counts=coat_counts,
            zone_comp_counts=zone_counts,
            comp_report_counts={c: len(rset) for c, rset in rep_by_comp.items()},
            comp_site_counts=site_by_comp,
            cooccurrence_sets=cooccur,
            calibrated_reports=len(all_reports),
            data_release=data_release,
        )

    def infer_material_family(
        self,
        site: SiteAggregate,
        chemistry_raw: Optional[str] = None,
        coating_state: str = "UNKNOWN",
        coating_type: Optional[str] = None,
    ) -> Dict[str, object]:
        """Infer material family distribution from EDS spectrum and/or analyst chemistry."""
        analyst_fam = map_chemistry_to_family(chemistry_raw)
        scores: Dict[str, float] = {}
        sup_by_fam: Dict[str, List[str]] = {}
        con_by_fam: Dict[str, List[str]] = {}

        if site.n_valid_spectra > 0 and site.metal_basis:
            mb = site.metal_basis
            for fid in MATERIAL_FAMILIES:
                ev = evaluate_domain_family(site, fid, coating_state, coating_type)
                sup_by_fam[fid] = ev.supporting_elements
                con_by_fam[fid] = ev.contradicting_elements
                if ev.outcome == "VETO":
                    scores[fid] = -8.0
                else:
                    scores[fid] = ev.score_delta * 2.2

            # Fine-grained spectral discriminators on metal-basis
            fe = mb.get("Fe", 0.0)
            cr = mb.get("Cr", 0.0)
            mn = mb.get("Mn", 0.0)
            si = mb.get("Si", 0.0)
            zn = mb.get("Zn", 0.0)
            cu = mb.get("Cu", 0.0)
            ni = mb.get("Ni", 0.0)
            al = mb.get("Al", 0.0)
            w_mo = mb.get("W", 0.0) + mb.get("Mo", 0.0)

            if fe >= 98.5 and cr < 0.25 and mn < 0.35 and si < 0.35:
                scores["PURE_IRON_SOFT_MAGNETIC"] = scores.get("PURE_IRON_SOFT_MAGNETIC", 0.0) + 2.6
            if fe >= 94.0 and 1.15 <= cr <= 2.3 and si < 1.0:
                scores["BEARING_100CR6"] = scores.get("BEARING_100CR6", 0.0) + 3.2
            if fe >= 93.0 and si >= 1.05 and 0.4 <= cr <= 1.2:
                scores["SPRING_CR_SI_STEEL"] = scores.get("SPRING_CR_SI_STEEL", 0.0) + 3.4
            if fe >= 93.0 and cr < 0.6 and 0.55 <= mn <= 1.10 and si < 0.8:
                scores["PLAIN_C_STEEL"] = scores.get("PLAIN_C_STEEL", 0.0) + 2.2
                if coating_type == "ZnP":
                    scores["LEADED_PLAIN_C"] = scores.get("LEADED_PLAIN_C", 0.0) + 1.8
            if fe >= 93.0 and mn >= 1.05 and cr < 0.8:
                scores["MN_CR_MN_STEEL"] = scores.get("MN_CR_MN_STEEL", 0.0) + 2.4
                scores["FREE_CUTTING_RESULPH_ETG"] = scores.get("FREE_CUTTING_RESULPH_ETG", 0.0) + 2.3
            if w_mo >= 5.0 and cr >= 3.0:
                scores["HSS_TOOL_STEEL"] = scores.get("HSS_TOOL_STEEL", 0.0) + 4.0
            if cr >= 15.0 and ni >= 6.5:
                scores["AUSTENITIC_SS"] = scores.get("AUSTENITIC_SS", 0.0) + 4.0
            if cu >= 50.0:
                scores["CU_SN_BRONZE"] = scores.get("CU_SN_BRONZE", 0.0) + 4.0
            if ni >= 70.0:
                scores["NI_ALLOY_PLATING"] = scores.get("NI_ALLOY_PLATING", 0.0) + 4.0
            if zn >= 50.0 and coating_state in ("COATED", "UNKNOWN") and fe < 45.0:
                scores["ZN_FLAKES_PLATING"] = scores.get("ZN_FLAKES_PLATING", 0.0) + 3.5
            if (al + si) >= 60.0 and fe < 15.0:
                scores["CERAMIC_SILICA_CARBO"] = scores.get("CERAMIC_SILICA_CARBO", 0.0) + 3.5
        elif site.n_valid_spectra > 0 and site.c_o_load >= 85.0:
            scores["CARBON_POLYMER_NONMETAL"] = 3.5

        if analyst_fam:
            scores[analyst_fam] = scores.get(analyst_fam, 0.0) + 3.2

        if not scores:
            return {
                "family_id": "UNKNOWN_FAMILY",
                "family_label": "Unknown / Insufficient Chemistry Evidence",
                "probability": 0.0,
                "source": "NONE",
                "probabilities": {},
            }

        max_s = max(scores.values())
        exps = {k: math.exp(v - max_s) for k, v in scores.items() if v > -7.0}
        tot = sum(exps.values()) + math.exp(-1.5 - max_s)
        probs = {k: round(v / tot, 4) for k, v in sorted(exps.items(), key=lambda x: x[1], reverse=True)}
        top_id = next(iter(probs)) if probs else "UNKNOWN_FAMILY"
        top_p = probs.get(top_id, 0.0)
        src = "SPECTRUM_AND_CHEMISTRY" if (site.n_valid_spectra > 0 and analyst_fam) else ("SPECTRUM" if site.n_valid_spectra > 0 else "CHEMISTRY_LABEL")
        return {
            "family_id": top_id,
            "family_label": MATERIAL_FAMILIES.get(top_id, top_id),
            "probability": top_p,
            "source": src,
            "analyst_family_id": analyst_fam,
            "probabilities": dict(list(probs.items())[:5]),
            "supporting_elements": sup_by_fam.get(top_id, []),
            "contradicting_elements": con_by_fam.get(top_id, []),
        }

    def _score_fingerprint(
        self,
        site: SiteAggregate,
        fp: ComponentReferenceFingerprint,
        coating_type: Optional[str],
    ) -> Tuple[Optional[float], List[str], List[str]]:
        """Compute robust fingerprint similarity (0..1) and supporting/contradicting elements."""
        if site.n_valid_spectra == 0 or not site.metal_basis or fp.n_sites == 0 or not fp.elements:
            return None, [], []

        mb = dict(site.metal_basis)
        # Decouple surface ZnP/Zn coating when comparing against bulk steel fingerprint
        if coating_type in ("ZnP", "Zn") and "Zn" in mb and "Zn" not in fp.elements and mb.get("Fe", 0.0) > 40.0:
            non_zn = {k: v for k, v in mb.items() if k not in ("Zn", "P")}
            s_nz = sum(non_zn.values())
            if s_nz > 10.0:
                mb = {k: round(v * 100.0 / s_nz, 4) for k, v in non_zn.items()}

        sup: List[str] = []
        con: List[str] = []
        wz2 = 0.0
        wsum = 0.0
        for el, st in fp.elements.items():
            if st.frequency < 0.30:
                continue
            v = mb.get(el)
            if v is None:
                # If element was reported as 0 or absent while expected > 0.5 wt%
                if st.median >= 0.55 and len(mb) >= 1:
                    con.append(el)
                    wz2 += 2.0 * (3.5 ** 2)
                    wsum += 2.0
                continue
            w = 0.8 if el == "Fe" else 2.2
            sig = max(st.sigma_eff, site.metal_basis_sigma.get(el, 0.2))
            z = abs(v - st.median) / max(0.20, sig)
            wz2 += w * min(z, 5.0) ** 2
            wsum += w
            if z <= 2.5:
                sup.append(el)
            else:
                con.append(el)

        # Check foreign elements in spectrum not in fingerprint
        for el, v in mb.items():
            if el not in fp.elements and v >= 0.55:
                con.append(el)
                wz2 += 2.0 * (3.5 ** 2)
                wsum += 2.0

        if wsum <= 0:
            return None, sup, con
        mean_z = math.sqrt(wz2 / wsum)
        sim = round(math.exp(-0.35 * (mean_z ** 2)), 4)
        return sim, sup, con

    def predict(
        self,
        spectra_inputs: List[Dict[str, float]],
        chemistry_raw: Optional[str] = None,
        surface_coating_raw: Optional[str] = None,
        location_raw: Optional[str] = None,
        site_uid: str = "query_site",
        report_id: str = "query_report",
    ) -> UnifiedPredictionResult:
        """Run unified internal-source prediction for a particle/site."""
        decoded = [decode_row(s) for s in spectra_inputs if s]
        site = aggregate_site_spectra(site_uid=site_uid, report_id=report_id, spectra=decoded)
        c_state, c_type, c_basis = normalize_coating(surface_coating_raw)
        loc_zone, _ = map_location_zone(location_raw, None)

        fam_info = self.infer_material_family(site, chemistry_raw, c_state, c_type)
        top_fam = str(fam_info.get("family_id", "UNKNOWN_FAMILY"))
        fam_probs: Dict[str, float] = fam_info.get("probabilities", {})  # type: ignore[assignment]
        analyst_fam = fam_info.get("analyst_family_id")

        # Non-metallic / external contaminant gate
        if top_fam in ("CARBON_POLYMER_NONMETAL", "ZN_FLAKES_PLATING") and analyst_fam in ("CARBON_POLYMER_NONMETAL", "ZN_FLAKES_PLATING"):
            # Only Viton Ring or HPP/Sleeve/Union Nut if explicitly matching, otherwise external contaminant
            if top_fam == "CARBON_POLYMER_NONMETAL" and (not chemistry_raw or "viton" not in chemistry_raw.lower()):
                return self._build_unknown_result(
                    site, fam_info, c_state, c_type, c_basis, loc_zone, location_raw,
                    reason="Non-metallic / carbon-base chemistry corresponds to external contaminants (fibers, paper, dusters, plastic) rather than an internal metallic injector component.",
                )

        candidates: List[CandidatePrediction] = []
        for spec in INTERNAL_COMPONENTS:
            cid = spec.component_id
            fp = self.fingerprints.get(cid)

            # 1. Family compatibility score (joint soft marginalization over family probabilities)
            fam_compat = sum(fam_probs.get(f, 0.0) for f in spec.compatible_families)
            if analyst_fam and analyst_fam in spec.compatible_families:
                # Check empirical P(cid | analyst_fam) from partial-label EM
                f_table = self.family_comp_counts.get(analyst_fam, {})
                f_tot = sum(f_table.values())
                emp_p = (f_table.get(cid, 0.0) + 0.35) / (f_tot + 3.0) if f_tot > 0 else 0.15
                fam_compat = max(fam_compat, round(0.55 + 0.45 * min(1.0, emp_p * 3.0), 4))

            # 2. Fingerprint similarity
            fp_sim, fp_sup, fp_con = self._score_fingerprint(site, fp, c_type) if fp else (None, [], [])

            # 3. Rule engine evaluation
            rule_evs = evaluate_component_domain_rules(site, cid, top_fam if top_fam != "UNKNOWN_FAMILY" else None, analyst_fam, c_state, c_type)
            if any(e.outcome == "VETO" for e in rule_evs):
                continue
            rule_delta = sum(e.score_delta for e in rule_evs)
            r_sup = [el for e in rule_evs for el in e.supporting_elements]
            r_con = [el for e in rule_evs for el in e.contradicting_elements]

            # 4. Surface / coating compatibility
            coat_key = c_type or c_state
            c_table = self.coating_comp_counts.get(coat_key, {})
            c_tot = sum(c_table.values())
            coat_sc = 0.0
            if c_state in ("COATED", "TRACES") and c_type:
                if c_type in spec.expected_coatings:
                    coat_sc = 0.35 + (0.25 * (c_table.get(cid, 0.0) / max(1.0, c_tot)))
                elif cid == "MAGNET_CORE":
                    coat_sc = -0.85
                else:
                    coat_sc = -0.15
            elif c_state == "NONE":
                if not spec.expected_coatings:
                    coat_sc = 0.15

            # 5. Particle location context (strictly capped at <= 0.15 to prevent shortcut leakage)
            loc_leak = bool(location_raw and re.search(spec.pattern, location_raw.lower()))
            loc_sc = 0.0
            if loc_zone not in ("UNKNOWN_ZONE", "OTHER_ZONE") and not loc_leak:
                z_table = self.zone_comp_counts.get(loc_zone, {})
                z_tot = sum(z_table.values())
                if z_tot > 0 and cid in z_table:
                    loc_sc = min(0.15, round(0.15 * (z_table[cid] / z_tot), 4))

            # 6. Historical support & uncertainty
            n_rep = self.comp_report_counts.get(cid, 0)
            n_sit = self.comp_site_counts.get(cid, 0)
            hist_bonus = min(0.25, 0.05 * math.log1p(n_rep))
            unc_pen = 0.0
            if site.n_valid_spectra == 0:
                unc_pen += 0.18
            elif "SINGLE_SPECTRUM" in site.flags:
                unc_pen += 0.06

            # Unified log-score combination
            if fam_compat < 0.03 and (fp_sim is None or fp_sim < 0.25):
                continue

            spec_term = (1.6 * (fp_sim - 0.5)) if fp_sim is not None else 0.0
            total_log_score = (
                1.8 * math.log(max(0.02, fam_compat))
                + spec_term
                + 0.45 * rule_delta
                + coat_sc
                + loc_sc
                + hist_bonus
                - unc_pen
            )
            compat_score = round(1.0 / (1.0 + math.exp(-total_log_score)), 4)

            sup_merged = list(dict.fromkeys(fp_sup + r_sup + fam_info.get("supporting_elements", [])))  # type: ignore[arg-type]
            con_merged = list(dict.fromkeys(fp_con + r_con + fam_info.get("contradicting_elements", [])))  # type: ignore[arg-type]

            candidates.append(CandidatePrediction(
                component_id=cid,
                component_name=spec.canonical_name,
                probability=0.0,
                compatibility_score=compat_score,
                family_compatibility=round(fam_compat, 4),
                fingerprint_similarity=fp_sim,
                rule_score=round(rule_delta, 4),
                coating_score=round(coat_sc, 4),
                location_score=round(loc_sc, 4),
                historical_reports=n_rep,
                historical_sites=n_sit,
                trust_level=fp.trust_level if fp else 1,
                supporting_elements=sup_merged,
                contradicting_elements=con_merged,
                rule_reasons=[e.reason for e in rule_evs if e.reason],
                indistinguishability_group=spec.indistinguishability_group,
            ))

        if not candidates:
            return self._build_unknown_result(
                site, fam_info, c_state, c_type, c_basis, loc_zone, location_raw,
                reason="No internal injector component is compatible with the observed elemental composition and constraints.",
            )

        candidates.sort(key=lambda c: (c.compatibility_score, c.historical_reports), reverse=True)

        # Convert compatibility scores into normalized posterior probabilities with an explicit UNKNOWN mass
        top_compat = candidates[0].compatibility_score
        unk_logit = -0.2 if top_compat >= 0.45 else 1.2
        raw_weights = [math.exp(3.2 * (c.compatibility_score - top_compat)) for c in candidates[:8]]
        unk_weight = math.exp(unk_logit - 3.2 * top_compat)
        w_tot = sum(raw_weights) + unk_weight
        for idx, c in enumerate(candidates):
            if idx < len(raw_weights):
                c.probability = round(raw_weights[idx] / w_tot, 4)
            else:
                c.probability = 0.0
        unk_prob = round(unk_weight / w_tot, 4)

        # Filter to meaningful candidate set (conformal threshold >= 0.08 probability or within 0.12 compat of top)
        active = [c for c in candidates[:6] if c.probability >= 0.08 or (top_compat - c.compatibility_score) <= 0.12]
        if not active:
            active = candidates[:1]

        top = active[0]
        runner_up = active[1] if len(active) > 1 else None
        margin = (top.compatibility_score - runner_up.compatibility_score) if runner_up else 1.0

        # Check indistinguishability group membership among top active candidates
        shared_group_id = None
        if runner_up and top.indistinguishability_group and top.indistinguishability_group == runner_up.indistinguishability_group and margin < 0.18:
            shared_group_id = top.indistinguishability_group
        elif top.indistinguishability_group and top.component_id != "MAGNET_CORE":
            # Check if other group members are also in active with close compatibility
            same_grp = [c for c in active if c.indistinguishability_group == top.indistinguishability_group and (top.compatibility_score - c.compatibility_score) <= 0.15]
            if len(same_grp) >= 2:
                shared_group_id = top.indistinguishability_group

        # Decision policy: HIGH_CONFIDENCE vs AMBIGUOUS vs UNKNOWN
        if top.compatibility_score < 0.35 or unk_prob > 0.45:
            status = "UNKNOWN"
            pred_name = None
            pred_id = None
            conf = round(1.0 - unk_prob, 4)
        elif (
            len(active) == 1
            or (margin >= 0.18 and shared_group_id is None and not top.contradicting_elements and top.historical_reports >= 2)
        ):
            status = "HIGH_CONFIDENCE"
            pred_name = top.component_name
            pred_id = top.component_id
            conf = round(min(0.96, top.compatibility_score), 4)
        else:
            status = "AMBIGUOUS"
            pred_name = None
            pred_id = None
            conf = round(sum(c.probability for c in active[:3]), 4)

        grp_obj = None
        if shared_group_id and shared_group_id in INDISTINGUISHABILITY_GROUPS:
            g = INDISTINGUISHABILITY_GROUPS[shared_group_id]
            grp_obj = {
                "group_id": shared_group_id,
                "label": g["label"],
                "members": [COMPONENT_BY_ID[m].canonical_name for m in g["members"] if m in COMPONENT_BY_ID],  # type: ignore[index]
                "reason": g["reason"],
            }

        expl = self._build_explanation(status, pred_name, active, fam_info, grp_obj, site, c_state, c_type)
        return UnifiedPredictionResult(
            prediction_status=status,
            predicted_component=pred_name,
            predicted_component_id=pred_id,
            confidence=conf,
            material_family=fam_info,
            candidates=active,
            indistinguishability_group=grp_obj,
            supporting_elements=top.supporting_elements,
            contradicting_elements=top.contradicting_elements,
            spectrum_quality={
                "quality_score": site.quality_score,
                "n_spectra": site.n_spectra,
                "n_valid_spectra": site.n_valid_spectra,
                "heterogeneity": site.heterogeneity,
                "c_o_load_wt_pct": site.c_o_load,
                "flags": site.flags,
            },
            location_evidence={
                "raw_location": location_raw,
                "zone": loc_zone,
                "score_contribution": top.location_score,
                "capped": True,
            },
            surface_coating_evidence={
                "raw_coating": surface_coating_raw,
                "state": c_state,
                "coating_type": c_type,
                "basis": c_basis,
                "score_contribution": top.coating_score,
            },
            unknown_probability=unk_prob,
            explanation=expl,
            model_metadata={
                "engine": "UnifiedISPEngine v2.0",
                "data_release": self.data_release,
                "calibrated_on_reports": self.calibrated_reports,
            },
        )

    def _build_unknown_result(
        self,
        site: SiteAggregate,
        fam_info: Dict[str, object],
        c_state: str,
        c_type: Optional[str],
        c_basis: str,
        loc_zone: str,
        location_raw: Optional[str],
        reason: str,
    ) -> UnifiedPredictionResult:
        return UnifiedPredictionResult(
            prediction_status="UNKNOWN",
            predicted_component=None,
            predicted_component_id=None,
            confidence=0.0,
            material_family=fam_info,
            candidates=[],
            indistinguishability_group=None,
            supporting_elements=list(fam_info.get("supporting_elements", [])),  # type: ignore[arg-type]
            contradicting_elements=list(fam_info.get("contradicting_elements", [])),  # type: ignore[arg-type]
            spectrum_quality={
                "quality_score": site.quality_score,
                "n_spectra": site.n_spectra,
                "n_valid_spectra": site.n_valid_spectra,
                "heterogeneity": site.heterogeneity,
                "c_o_load_wt_pct": site.c_o_load,
                "flags": site.flags,
            },
            location_evidence={"raw_location": location_raw, "zone": loc_zone, "score_contribution": 0.0, "capped": True},
            surface_coating_evidence={"raw_coating": None, "state": c_state, "coating_type": c_type, "basis": c_basis, "score_contribution": 0.0},
            unknown_probability=1.0,
            explanation=f"UNKNOWN: {reason}",
            model_metadata={
                "engine": "UnifiedISPEngine v2.0",
                "data_release": self.data_release,
                "calibrated_on_reports": self.calibrated_reports,
            },
        )

    def _build_explanation(
        self,
        status: str,
        pred_name: Optional[str],
        active: List[CandidatePrediction],
        fam_info: Dict[str, object],
        grp_obj: Optional[Dict[str, object]],
        site: SiteAggregate,
        c_state: str,
        c_type: Optional[str],
    ) -> str:
        fam_lbl = fam_info.get("family_label", "Unknown")
        if status == "HIGH_CONFIDENCE" and pred_name:
            sup_str = ", ".join(active[0].supporting_elements) if active[0].supporting_elements else "chemistry profile"
            return (
                f"HIGH CONFIDENCE: Identified as {pred_name} within material family '{fam_lbl}'. "
                f"Supported by {sup_str} across {site.n_valid_spectra} spectrum(s) and {active[0].historical_reports} validated reference reports."
            )
        if status == "AMBIGUOUS":
            names = ", ".join(f"{c.component_name} ({c.compatibility_score:.2f})" for c in active[:4])
            grp_txt = f" [{grp_obj['label']}: {grp_obj['reason']}]" if grp_obj else ""
            return (
                f"AMBIGUOUS: Material family '{fam_lbl}' (coating={c_type or c_state}) is compatible with multiple internal components: "
                f"{names}.{grp_txt} EDS chemistry alone cannot uniquely separate these candidates without teardown/geometric inspection."
            )
        return f"UNKNOWN: Insufficient evidence to reliably identify an internal injector component (family={fam_lbl})."
