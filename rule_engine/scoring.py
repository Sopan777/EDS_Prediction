"""
rule_engine/scoring.py
======================
Compatibility scoring with three-state feasibility, ratio gates and abstention.

This replaces the conjunctive AND filter in ``rule_engine.engine``, where a rule
fired only if every condition passed and the reported confidence was a constant
frozen at training time - identical for every input that matched, and therefore
carrying no information about how well *this* spectrum fits.

Three ideas do the real work
----------------------------
1. **Absence can never satisfy a constraint.** Every check is evaluated against
   the measurement STATE, not a coerced float. An element that was never
   analysed makes a family *unevaluable*; it never passes. That single change
   removes the failure class where ``{S: 0.2}`` returned a component whose every
   reference spectrum contained 1.12-1.60 wt% Mn.

2. **Positive evidence is required, and foreign elements are rejected.** A
   family must have its required elements actually observed, and a composition
   carrying a large amount of something the family does not contain is refused.
   The old rules had 65 missing lower bounds and 351 missing upper bounds, so
   neither direction was enforced.

3. **Confidence is computed, and abstention is a first-class answer.**
   Compatibility combines fit, evidence sufficiency and basis quality, and is
   deliberately capped below 1.00: with five real labelled particles no honest
   probability calibration is possible, and a goodness-of-fit statistic must not
   be dressed up as a posterior.

Stdlib only.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rule_engine.normalize import (  # noqa: E402
    NormalizedSpectrum,
    State,
    normalize_spectrum,
)

KNOWLEDGE_PATH = Path(__file__).resolve().parent / "knowledge" / "materials.json"

# --- tuning constants -------------------------------------------------------
# All are exposed here rather than buried in code, and all are justified.

#: Sigma multiplier for HARD rejection. A measured value must be outside the
#: band by more than this before a family is refused outright. 3 sigma is the
#: usual "beyond reasonable measurement error" line and keeps genuine members
#: of a family inside their own band.
K_HARD = 3.0

#: A measured element the family does not contain at all is a foreign element.
#: It only refuses the family once it exceeds this share of the metal basis;
#: below it, the reading is consistent with a residue or a trace.
FOREIGN_ELEMENT_MAX_PCT = 2.0

#: Minimum share of the as-measured spectrum that must be alloy elements before
#: any material claim is made. Set below the ~24 wt% of the real bronze
#: particle, whose spectrum is ~75% C+O+F from a PTFE-loaded seal ring.
MIN_ALLOY_SIGNAL_PCT = 8.0

#: Minimum evidence sufficiency to emit a single family rather than a set.
MIN_EVIDENCE = 0.5

#: Minimum compatibility before any family may be reported at all. Clearing the
#: hard constraints is necessary but not sufficient: a family can be
#: non-contradicted and still fit badly. Without this floor, several candidates
#: scoring ~0 produced a tiny margin and the answer came back AMBIGUOUS between
#: families none of which was supported.
MIN_COMPATIBILITY = 0.15

#: Compatibility ceiling for a spectrum carrying a data-quality error (a
#: negative wt%, a value above 100, or a duplicate key). Such input may still
#: be identifiable, but it must never be reported as a clean high-confidence
#: result - the analyst has to see that the input itself was suspect.
DATA_QUALITY_COMPATIBILITY_CAP = 0.45

#: Minimum compatibility margin between the top two families. Below this the
#: answer is an ambiguous SET - which is a legitimate result, and what the
#: analysts themselves report when they write "Magnet Nut, NR nut??".
MIN_MARGIN = 0.15

#: Compatibility is a goodness-of-fit statistic, never a probability, so it is
#: capped short of certainty no matter how well a spectrum fits.
MAX_COMPATIBILITY = 0.95


class Verdict(str, Enum):
    """Outcome of evaluating one family against one spectrum."""

    FEASIBLE = "feasible"
    #: A decisive element was never analysed - cannot confirm or refute.
    UNEVALUABLE = "unevaluable"
    #: A required element was analysed and absent, or a value is out of band.
    CONTRADICTED = "contradicted"


class Decision(str, Enum):
    """Overall decision for a spectrum or particle.

    IDENTIFIED       - evidence clearly separates the top candidate.
    AMBIGUOUS        - multiple candidates have similar scores.
    UNKNOWN          - composition does not match any known material.
    INSUFFICIENT_DATA - too few useful EDS elements to make any claim.
    CONFLICT         - declared material metadata contradicts measured composition.
    """

    IDENTIFIED = "identified"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"
    INSUFFICIENT_DATA = "insufficient_data"
    CONFLICT = "conflict"


@dataclass
class Check:
    """One constraint evaluation, retained so any answer can be explained."""

    kind: str  # band | required | forbidden | ratio | foreign
    element: str
    passed: bool
    detail: str
    z: Optional[float] = None

    def to_dict(self) -> dict:
        d = {
            "kind": self.kind,
            "element": self.element,
            "passed": self.passed,
            "detail": self.detail,
        }
        if self.z is not None:
            d["z"] = round(self.z, 2)
        return d


@dataclass
class FamilyScore:
    """Result of scoring one family."""

    family_id: str
    label: str
    grade_hint: str
    verdict: Verdict
    compatibility: float = 0.0
    distance2: float = 0.0
    evidence: float = 0.0
    checks: List[Check] = field(default_factory=list)
    blocking: List[str] = field(default_factory=list)
    unevaluable_elements: List[str] = field(default_factory=list)
    #: Measured elements outside this family's band that were not decisive
    #: enough to veto it. They cost compatibility and must stay visible: an
    #: unexplained element is exactly what an analyst needs to see.
    unexplained_elements: List[str] = field(default_factory=list)
    provisional: bool = False
    candidate_components: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "family_id": self.family_id,
            "label": self.label,
            "grade_hint": self.grade_hint,
            "verdict": self.verdict.value,
            "compatibility": round(self.compatibility, 4),
            "distance2": round(self.distance2, 4),
            "evidence": round(self.evidence, 3),
            "blocking": list(self.blocking),
            "unevaluable_elements": list(self.unevaluable_elements),
            "unexplained_elements": list(self.unexplained_elements),
            "provisional": self.provisional,
            "candidate_components": list(self.candidate_components),
            "checks": [c.to_dict() for c in self.checks],
        }


@dataclass
class Prediction:
    """Final answer for one spectrum or pooled particle."""

    decision: Decision
    families: List[FamilyScore] = field(default_factory=list)
    margin: float = 0.0
    reason: str = ""
    caveats: List[str] = field(default_factory=list)
    quality: Dict[str, float] = field(default_factory=dict)

    @property
    def top(self) -> Optional[FamilyScore]:
        """The leading family, or None when the engine abstained.

        There is no top family when we abstained. On the UNKNOWN path
        ``families`` carries every family that was *considered*, including
        contradicted ones, purely so the answer can be explained - returning
        the first of those would report a titanium alloy as "plain carbon
        steel", which is the exact class of misleading output this engine
        exists to eliminate.
        """
        if self.decision is Decision.UNKNOWN:
            return None
        return self.families[0] if self.families else None

    @property
    def considered(self) -> List[FamilyScore]:
        """Every family evaluated, for explanation regardless of decision."""
        return list(self.families)

    @property
    def candidate_components(self) -> List[str]:
        """Components consistent with the answer actually given.

        Scoped to the decision, because a candidate list is a claim:

        * UNKNOWN - no claim. ``families`` holds every family considered, only
          so the abstention can be explained; listing their components would
          hand the analyst a shortlist we just said we could not support.
        * IDENTIFIED - only the identified family's components. Unioning the
          also-feasible runners-up made the list contradict the caveat that
          counts them (23 listed against 15 stated).
        * AMBIGUOUS - the union across the tied families, which IS the answer:
          the set is what the analysts themselves report as "Magnet Nut,
          NR nut??".
        """
        if self.decision in (
            Decision.UNKNOWN, Decision.INSUFFICIENT_DATA, Decision.CONFLICT
        ):
            return []
        sources = (
            self.families[:1] if self.decision is Decision.IDENTIFIED else self.families
        )
        out: List[str] = []
        for f in sources:
            for c in f.candidate_components:
                if c not in out:
                    out.append(c)
        return out

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "material_family": self.top.label if self.top else None,
            "grade_hint": self.top.grade_hint if self.top else None,
            "compatibility": round(self.top.compatibility, 4) if self.top else 0.0,
            "margin": round(self.margin, 4),
            "reason": self.reason,
            "candidate_components": self.candidate_components,
            "caveats": list(self.caveats),
            "quality": {k: round(v, 4) for k, v in self.quality.items()},
            "families": [f.to_dict() for f in self.families],
        }


class KnowledgeBase:
    """The derived material knowledge base."""

    def __init__(self, data: dict):
        self.version: str = data.get("version", "unknown")
        self.families: Dict[str, dict] = data.get("families", {})
        self.components: Dict[str, dict] = data.get("components", {})
        self.caveats: List[str] = data.get("caveats", [])
        self._known_elements: Optional[set] = None

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "KnowledgeBase":
        p = Path(path) if path else KNOWLEDGE_PATH
        if not p.exists():
            raise FileNotFoundError(
                str(p)
                + " not found. Generate it with:\n"
                + "    python training/derive_sigma_model.py\n"
                + "    python training/derive_knowledge.py"
            )
        data = json.loads(p.read_text(encoding="utf-8"))

        # validator.py's checks were audited as never being called at
        # runtime for the retired rules.json either - fixing that here so
        # a structurally broken knowledge base fails loudly at load time
        # instead of scoring silently wrong deep inside score_family.
        from rule_engine.validator import validate_knowledge_base

        report = validate_knowledge_base(data)
        if not report["is_valid"]:
            raise ValueError(
                str(p)
                + " failed validation:\n  "
                + "\n  ".join(report["issues"])
            )

        kb = cls(data)
        return kb

    def components_for(self, family_id: str) -> List[str]:
        return list(self.families.get(family_id, {}).get("components", []))

    def known_elements(self) -> set:
        """Every alloy element described by ANY family, cached on first use.

        This is the reference set for novelty detection: an alloy element
        outside it was never seen in any real spectrum this knowledge base was
        built from, which is a different and stronger signal than being
        "foreign" to one particular family (§12's OOD-detection gap - no
        labels needed, since the knowledge base itself already is the
        reference distribution).
        """
        if self._known_elements is None:
            known: set = set()
            for fam in self.families.values():
                known.update(fam.get("elements", {}).keys())
            self._known_elements = known
        return self._known_elements


_KB: Optional[KnowledgeBase] = None


def get_knowledge_base() -> KnowledgeBase:
    global _KB
    if _KB is None:
        _KB = KnowledgeBase.load()
    return _KB


def _parse_ratio(name: str) -> Tuple[str, str]:
    a, _, b = name.partition("/")
    return a.strip(), b.strip()


def _has_data_quality_error(spectrum: NormalizedSpectrum) -> bool:
    """True when the INPUT itself is suspect, not merely partial.

    Keys off the structured ``data_quality_errors`` the normaliser records
    (negative wt%, a total above 100, a duplicated key, an unparseable number)
    rather than matching warning text, so the two cannot drift apart. A
    legitimately partial composition is NOT a data-quality error.
    """
    return bool(spectrum.data_quality_errors)


def score_family(
    spectrum: NormalizedSpectrum, family_id: str, family: dict
) -> FamilyScore:
    """Evaluate one family against one normalised spectrum."""
    checks: List[Check] = []
    blocking: List[str] = []
    unevaluable: List[str] = []
    unexplained: List[str] = []
    z_terms: List[Tuple[float, float]] = []  # (z, weight)
    # Count of z_terms that CONFIRM the family (a required/discriminating
    # element measured in-band, or a ratio in-band) - as opposed to the cost
    # applied for an incidental, non-decisive element sitting out of band.
    # The verdict must not promote to FEASIBLE on cost-only evidence.
    confirming = 0

    elements: Dict[str, dict] = family.get("elements", {})
    discriminators: List[str] = family.get("discriminators", [])

    # -- 1. required elements: must be observed, and in band ---------------
    for element, spec in elements.items():
        if not spec.get("required"):
            continue
        state = spectrum.state(element)
        if state is State.NOT_ANALYSED:
            # No information. Cannot confirm the family - and must not pass.
            unevaluable.append(element)
            checks.append(
                Check("required", element, False, "not analysed - cannot confirm")
            )
            continue
        if state is State.BELOW_LOD:
            # Analysed and absent is positive evidence AGAINST the family.
            blocking.append(element + " required but analysed and not detected")
            checks.append(
                Check("required", element, False, "analysed, below detection limit")
            )
            continue
        checks.append(Check("required", element, True, "present"))

    # -- 2. band checks on every measured element the family describes ------
    for element, spec in elements.items():
        if not spectrum.is_measured(element):
            continue
        value = spectrum.metal(element)
        sigma = spectrum.sigma(element) or 0.0
        if value is None:
            continue
        lo, hi = spec.get("band_wt", [0.0, 100.0])
        # An element whose absolute level is unreliable (trace-to-matrix role)
        # is checked loosely and carries its weight through a ratio instead.
        prefer_ratio = spec.get("prefer_ratio", False)
        tol = K_HARD * sigma * (2.0 if prefer_ratio else 1.0)
        out_of_band = value < lo - tol or value > hi + tol

        # Only an element that DEFINES the material may veto it, and only when
        # its band rests on enough real data to be trusted. An incidental minor
        # element must not: a Cr band derived from a single spectrum once
        # rejected the real bronze particle outright, even though Cu, Sn and the
        # Sn/Cu ratio all matched. Left unguarded, any stray contaminant becomes
        # a veto - the mirror image of the old engine's missing upper bounds.
        decisive = bool(spec.get("required")) or element in discriminators
        band_trusted = not spec.get("provisional", False)
        may_veto = decisive and band_trusted and not prefer_ratio

        if out_of_band and may_veto:
            blocking.append(
                element
                + " "
                + str(round(value, 2))
                + " outside "
                + str([lo, hi])
                + " wt%"
            )
            checks.append(
                Check(
                    "band",
                    element,
                    False,
                    str(round(value, 2)) + " outside " + str([lo, hi]),
                )
            )
            continue
        if out_of_band:
            # Not a veto, but genuinely unexplained: it must cost something.
            # The raw z is unbounded (the value can sit arbitrarily far outside
            # a thin band), and an element we just decided is NOT decisive
            # enough to veto the family must not be allowed to dominate the
            # distance term either - that defeats the reason it was exempted
            # from vetoing in the first place. On the real bronze particle an
            # incidental Cr reading (z=5.13, one-spectrum band) outweighed
            # near-perfect fits on Cu, Sn and the Sn/Cu ratio and pushed
            # compatibility to 0.02. Capping the z and down-weighting the term
            # keeps it a real but bounded cost.
            raw_z = (value - min(max(value, lo), hi)) / sigma if sigma > 0 else 0.0
            z = min(abs(raw_z), K_HARD)
            z_terms.append((z, 0.3))  # cost only - NOT confirming evidence
            checks.append(
                Check(
                    "band",
                    element,
                    False,
                    str(round(value, 2))
                    + " outside "
                    + str([lo, hi])
                    + " (unexplained, not decisive for this family)",
                    z=raw_z,
                )
            )
            unexplained.append(element)
            continue
        # Soft term: zero inside the band, so a legitimately wide range is not
        # penalised for a value sitting mid-band.
        clamped = min(max(value, lo), hi)
        z = (value - clamped) / sigma if sigma > 0 else 0.0
        weight = 0.3 if prefer_ratio else 1.0
        if element in discriminators:
            weight *= 3.0  # discriminators carry the most classification info
        # Matrix elements (Fe in steel, Cu in bronze, Ni in Ni-alloy) should
        # not dominate the distance: they sit in-band for nearly every family
        # of the same system and carry little classification information.
        is_matrix = value > 50.0 and not spec.get("required", False)
        if is_matrix and element not in discriminators:
            weight = min(weight, 0.5)
        z_terms.append((z, weight))
        # Only DECISIVE elements confirm this family. Fe sits inside almost
        # every steel family's band, so an in-band Fe reading must not by
        # itself promote a family - {Fe:68,Cr:30,Ni:1} once did exactly that
        # for F8a (Zn-coated steel) purely because Fe fell in its wide band,
        # even though Zn and Si, the elements that actually define it, were
        # never analysed.
        if decisive:
            confirming += 1
        checks.append(Check("band", element, True, "in band", z=z))

    # -- 3. foreign elements: something the family does not contain ---------
    for element in spectrum.alloy_elements():
        if element in elements:
            continue
        value = spectrum.metal(element) or 0.0
        if value > FOREIGN_ELEMENT_MAX_PCT:
            blocking.append(
                element
                + " "
                + str(round(value, 2))
                + " wt% not expected in this family"
            )
            checks.append(
                Check("foreign", element, False, str(round(value, 2)) + " wt% unexpected")
            )

    # -- 4. ratio gates ----------------------------------------------------
    ratio_specs = family.get("ratios", [])
    ratio_evaluated = 0
    for spec in ratio_specs:
        name = spec.get("ratio", "")
        a, b = _parse_ratio(name)
        got = spectrum.ratio(a, b)
        if got is None:
            checks.append(
                Check("ratio", name, False, "not evaluable (a term is missing or ~0)")
            )
            unevaluable.append(name)
            continue
        value, sigma = got
        lo, hi = spec.get("min", 0.0), spec.get("max", math.inf)
        ratio_evaluated += 1
        if value < lo - K_HARD * sigma or value > hi + K_HARD * sigma:
            blocking.append(
                name + " " + str(round(value, 3)) + " outside " + str([lo, hi])
            )
            checks.append(
                Check("ratio", name, False, str(round(value, 3)) + " outside band")
            )
        else:
            clamped = min(max(value, lo), hi)
            z = (value - clamped) / sigma if sigma > 0 else 0.0
            z_terms.append((z, 3.0))  # ratios are the strongest evidence
            confirming += 1
            checks.append(Check("ratio", name, True, str(round(value, 3)), z=z))

    # -- 5. verdict --------------------------------------------------------
    if blocking:
        verdict = Verdict.CONTRADICTED
    elif unevaluable and not confirming:
        # A required/discriminating element was never analysed, and nothing
        # else measured actually confirms this family. A cost-only penalty
        # from an incidental unexplained element does not count as support -
        # {Fe:68,Cr:30,Ni:1} once promoted F8a (Zn-coated steel) to FEASIBLE
        # this way despite Zn and Si, both required, never being analysed.
        verdict = Verdict.UNEVALUABLE
    else:
        verdict = Verdict.FEASIBLE

    # -- 6. evidence sufficiency ------------------------------------------
    # Share of this family's discriminators actually observed.
    needed = discriminators or list(elements)
    observed = 0
    for name in needed:
        if "/" in name:
            a, b = _parse_ratio(name)
            if spectrum.ratio(a, b) is not None:
                observed += 1
        elif spectrum.is_measured(name):
            observed += 1
    evidence = observed / len(needed) if needed else 0.0

    # -- 7. distance and compatibility ------------------------------------
    total_w = sum(w for _, w in z_terms)
    distance2 = (
        sum(w * z * z for z, w in z_terms) / total_w if total_w > 0 else 0.0
    )

    if verdict is Verdict.FEASIBLE:
        fit = math.exp(-0.5 * distance2)
        quality = 1.0 - min(spectrum.contamination_fraction, 0.9) * 0.15
        compatibility = min(
            MAX_COMPATIBILITY, fit * min(evidence, 1.0) * quality
        )
    else:
        compatibility = 0.0

    return FamilyScore(
        family_id=family_id,
        label=family.get("label", family_id),
        grade_hint=family.get("grade_hint", ""),
        verdict=verdict,
        compatibility=compatibility,
        distance2=distance2,
        evidence=evidence,
        checks=checks,
        blocking=blocking,
        unevaluable_elements=sorted(set(unevaluable)),
        unexplained_elements=sorted(set(unexplained)),
        provisional=bool(family.get("provisional")),
        candidate_components=list(family.get("components", [])),
    )


def predict_spectrum(
    values: Dict[str, object],
    analysed_elements: Optional[List[str]] = None,
    knowledge: Optional[KnowledgeBase] = None,
) -> Prediction:
    """Identify the material family for one spectrum.

    Returns a :class:`Prediction` that is always one of: a single family, an
    ambiguous set, or an explicit ``unknown``. It never returns a family name
    with a confidence that was not computed from this input.
    """
    kb = knowledge or get_knowledge_base()
    spectrum = normalize_spectrum(values, analysed_elements=analysed_elements)

    quality = {
        "alloy_signal_pct": spectrum.alloy_total,
        "contamination_fraction": spectrum.contamination_fraction,
        "coating_fraction": spectrum.coating_fraction,
        "n_alloy_elements": float(len(spectrum.alloy_elements())),
    }
    caveats: List[str] = list(spectrum.warnings)
    # Carbon is not quantifiable by EDS here, so no carbon grade can be claimed.
    caveats.append(
        "Carbon content is not determinable by EDS; grade is assigned on "
        "alloying elements only."
    )

    # Unsupervised novelty signal: an alloy element no family in the whole
    # knowledge base describes - not merely foreign to one family - means this
    # element was never seen in ANY real spectrum the knowledge base was built
    # from. Needs no labels: the knowledge base itself is the reference
    # distribution (§12 "Detect OOD compositions - legitimate now").
    novel_elements = sorted(
        e
        for e in spectrum.alloy_elements()
        if e not in kb.known_elements()
        and (spectrum.metal(e) or 0.0) > FOREIGN_ELEMENT_MAX_PCT
    )
    if novel_elements:
        caveats.append(
            "Novelty: "
            + ", ".join(novel_elements)
            + " above "
            + str(FOREIGN_ELEMENT_MAX_PCT)
            + " wt% on the alloy basis is not described by ANY family in the "
            + "reference set - this composition may be outside what this "
            + "knowledge base has ever measured, not merely a poor fit to a "
            + "known family."
        )

    # Gate 1: is there enough metal to talk about a material at all?
    if spectrum.alloy_total < MIN_ALLOY_SIGNAL_PCT:
        return Prediction(
            decision=Decision.UNKNOWN,
            reason=(
                "insufficient metal signal: alloy elements are only "
                + str(round(spectrum.alloy_total, 1))
                + " wt% of the spectrum"
            ),
            caveats=caveats,
            quality=quality,
        )

    scored = [
        score_family(spectrum, fid, fam) for fid, fam in kb.families.items()
    ]

    # A spectrum carrying a data-quality error may still be identifiable, but it
    # must not present as a clean result: a composition with a negative wt%, a
    # total of 9999, or a duplicated key once returned compatibility 0.95, which
    # tells the analyst nothing was wrong with their input.
    if _has_data_quality_error(spectrum):
        caveats.append(
            "Input data-quality problem detected; compatibility is capped and the "
            "result should be reviewed against the source spectrum."
        )
        for s in scored:
            s.compatibility = min(s.compatibility, DATA_QUALITY_COMPATIBILITY_CAP)

    feasible = [s for s in scored if s.verdict is Verdict.FEASIBLE]
    feasible.sort(key=lambda s: (-s.compatibility, s.family_id))

    # Gate 2: nothing survived the hard constraints.
    if not feasible:
        unevaluable = [s for s in scored if s.verdict is Verdict.UNEVALUABLE]
        if unevaluable:
            missing = sorted({e for s in unevaluable for e in s.unevaluable_elements})
            reason = (
                "insufficient evidence: no family could be confirmed because "
                + ", ".join(missing[:6])
                + " were not analysed"
            )
        else:
            reason = (
                "no known material is compatible with this composition "
                "(out of reference)"
            )
        return Prediction(
            decision=Decision.UNKNOWN,
            families=sorted(scored, key=lambda s: s.family_id),
            reason=reason,
            caveats=caveats,
            quality=quality,
        )

    top = feasible[0]
    runner = feasible[1] if len(feasible) > 1 else None
    margin = top.compatibility - (runner.compatibility if runner else 0.0)

    # Gate 2b: a family can clear the hard constraints and still fit terribly.
    # Without this, every candidate scoring ~0 produced a tiny margin and the
    # answer came back AMBIGUOUS between families it did not actually support -
    # e.g. a 30 wt% Cr composition reported as ambiguous 'Zn-coated steel' at
    # compatibility 0.00. Zero support is an abstention, not an ambiguity.
    if top.compatibility < MIN_COMPATIBILITY:
        return Prediction(
            decision=Decision.UNKNOWN,
            families=feasible,
            margin=margin,
            reason=(
                "no material fits well enough: best candidate ("
                + top.label
                + ") reaches only "
                + str(round(top.compatibility, 3))
                + " compatibility"
            ),
            caveats=caveats,
            quality=quality,
        )

    # Gate 3: enough of the deciding elements actually measured?
    if top.evidence < MIN_EVIDENCE:
        return Prediction(
            decision=Decision.UNKNOWN,
            families=feasible,
            margin=margin,
            reason=(
                "insufficient evidence: only "
                + str(round(top.evidence * 100))
                + "% of the deciding elements for "
                + top.label
                + " were measured"
            ),
            caveats=caveats,
            quality=quality,
        )

    # Gate 4: is the leader actually separated from the field?
    if runner is not None and margin < MIN_MARGIN:
        tied = [s for s in feasible if top.compatibility - s.compatibility < MIN_MARGIN]
        return Prediction(
            decision=Decision.AMBIGUOUS,
            families=tied,
            margin=margin,
            reason=(
                "ambiguous between "
                + ", ".join(s.label for s in tied)
                + " - separation is within measurement uncertainty"
            ),
            caveats=caveats,
            quality=quality,
        )

    if top.provisional:
        caveats.append(
            "Family '"
            + top.label
            + "' rests on limited reference data; treat its bands as indicative."
        )
    if len(top.candidate_components) > 1:
        caveats.append(
            "Component identity is not determinable from EDS composition alone: "
            + str(len(top.candidate_components))
            + " components share this material family."
        )

    return Prediction(
        decision=Decision.IDENTIFIED,
        families=feasible,
        margin=margin,
        reason="compatible with " + top.label,
        caveats=caveats,
        quality=quality,
    )


def predict_particle(
    spectra: List[Dict[str, object]],
    analysed_elements: Optional[List[str]] = None,
    knowledge: Optional[KnowledgeBase] = None,
) -> Prediction:
    """Identify the material for a particle measured with several spectra.

    Evidence is POOLED rather than voted. The previous implementation took a
    majority vote and then averaged probability only over the spectra where the
    winner already led - a biased estimator that also hardcoded its low
    confidence flag to ``None``. Here every spectrum's family scores are
    combined, so repeat measurements sharpen the answer instead of outvoting
    each other, and a family contradicted by any spectrum cannot win.
    """
    kb = knowledge or get_knowledge_base()
    if not spectra:
        return Prediction(
            decision=Decision.UNKNOWN, reason="no spectra supplied"
        )
    if len(spectra) == 1:
        return predict_spectrum(spectra[0], analysed_elements, kb)

    per_spectrum = [predict_spectrum(s, analysed_elements, kb) for s in spectra]

    # Pool per family: mean compatibility over spectra, but any hard
    # contradiction anywhere disqualifies the family outright.
    pooled: Dict[str, FamilyScore] = {}
    contradicted: set = set()
    counts: Dict[str, int] = {}
    for pred in per_spectrum:
        for fs in pred.families:
            if fs.verdict is Verdict.CONTRADICTED:
                contradicted.add(fs.family_id)
            elif fs.verdict is Verdict.FEASIBLE:
                counts[fs.family_id] = counts.get(fs.family_id, 0) + 1
                cur = pooled.get(fs.family_id)
                if cur is None:
                    pooled[fs.family_id] = fs
                else:
                    cur.compatibility += fs.compatibility
                    cur.distance2 += fs.distance2
                    cur.evidence = max(cur.evidence, fs.evidence)

    survivors: List[FamilyScore] = []
    for fid, fs in pooled.items():
        if fid in contradicted:
            continue
        n = counts[fid]
        fs.compatibility /= n
        fs.distance2 /= n
        # Pooling across independent spectra is genuine corroboration, so a
        # family seen in every spectrum is rewarded over one seen in a few.
        fs.compatibility *= min(1.0, 0.6 + 0.4 * n / len(spectra))
        survivors.append(fs)
    survivors.sort(key=lambda s: (-s.compatibility, s.family_id))

    caveats: List[str] = []
    for pred in per_spectrum:
        for c in pred.caveats:
            if c not in caveats:
                caveats.append(c)

    quality = {
        "n_spectra": float(len(spectra)),
        "alloy_signal_pct": sum(
            p.quality.get("alloy_signal_pct", 0.0) for p in per_spectrum
        )
        / len(per_spectrum),
        "contamination_fraction": sum(
            p.quality.get("contamination_fraction", 0.0) for p in per_spectrum
        )
        / len(per_spectrum),
    }

    if not survivors:
        return Prediction(
            decision=Decision.UNKNOWN,
            reason=(
                "no family is compatible with all "
                + str(len(spectra))
                + " spectra of this particle"
            ),
            caveats=caveats,
            quality=quality,
        )

    top = survivors[0]
    runner = survivors[1] if len(survivors) > 1 else None
    margin = top.compatibility - (runner.compatibility if runner else 0.0)

    # Same floor as predict_spectrum's Gate 2b: clearing the hard constraints
    # is necessary but not sufficient. Without this, a particle where every
    # family fits terribly (e.g. compatibility 0.11) could still be reported
    # as AMBIGUOUS between two poor fits rather than an honest abstention -
    # the pooled path had no equivalent of the single-spectrum floor.
    if top.compatibility < MIN_COMPATIBILITY:
        return Prediction(
            decision=Decision.UNKNOWN,
            families=survivors,
            margin=margin,
            reason=(
                "no material fits well enough across the pooled spectra: "
                "best candidate ("
                + top.label
                + ") reaches only "
                + str(round(top.compatibility, 3))
                + " compatibility"
            ),
            caveats=caveats,
            quality=quality,
        )

    if top.evidence < MIN_EVIDENCE:
        decision, reason = Decision.UNKNOWN, (
            "insufficient evidence across the pooled spectra for " + top.label
        )
        report = survivors
    elif runner is not None and margin < MIN_MARGIN:
        report = [
            s for s in survivors if top.compatibility - s.compatibility < MIN_MARGIN
        ]
        decision, reason = Decision.AMBIGUOUS, (
            "ambiguous between " + ", ".join(s.label for s in report)
        )
    else:
        decision, reason = Decision.IDENTIFIED, ("compatible with " + top.label)
        report = survivors
        # These may already be present from a per-spectrum prediction's own
        # caveats (deduped above) - append only if genuinely new, otherwise
        # a pooled particle whose top family also won each individual
        # spectrum ends up with the exact same caveat text twice.
        candidate_caveat = (
            "Component identity is not determinable from EDS composition "
            "alone: "
            + str(len(top.candidate_components))
            + " components share this material family."
        )
        if len(top.candidate_components) > 1 and candidate_caveat not in caveats:
            caveats.append(candidate_caveat)
        provisional_caveat = (
            "Family '"
            + top.label
            + "' rests on limited reference data; bands are indicative."
        )
        if top.provisional and provisional_caveat not in caveats:
            caveats.append(provisional_caveat)

    return Prediction(
        decision=decision,
        families=report,
        margin=margin,
        reason=reason,
        caveats=caveats,
        quality=quality,
    )
