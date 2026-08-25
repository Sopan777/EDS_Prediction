"""
rule_engine/normalize.py
========================
Input canonicalisation, three-state missingness, and dual-basis normalisation.

This module replaces the coercion in ``rule_engine.preprocessing.validate_input``
and ``data_utils.eds_values_to_feature_row``, both of which map a missing key,
``None``, ``""``, ``"-"`` and ``"N/A"`` all to ``0.0``. That single collapse is
the root cause of the audited failure class: because a "forbidden element" can
only be written ``<= 0.0``, an element that was never analysed satisfies it for
free, so sparse input is biased *toward* matching.

Three states, not two
---------------------
``MEASURED``      a real quantity, carrying a real uncertainty.
``BELOW_LOD``     analysed and not detected. This is positive evidence of
                  absence, bounded above by the detection limit - it can
                  legitimately *contradict* a grade that requires the element.
``NOT_ANALYSED``  never in the analysed set. Carries no information at all: it
                  can neither confirm nor contradict, and must instead reduce
                  evidence sufficiency so the engine can abstain.

The distinction is recoverable from the source reports. In an EDS table the
column set *is* the analysed set, so a blank cell under an existing column
means "analysed, not detected" (``BELOW_LOD``), while an element with no column
at all was never looked for (``NOT_ANALYSED``). ``eds_extractor`` already
computes that column set and then discards it.

Why a metal basis
-----------------
These reports are acquired with "All elements analysed (Normalised)", so every
spectrum is forced to sum to 100%. C, O, N and F come largely from the carbon
tape, surface oxide and mounting medium rather than from the material, so the
closure makes absolute wt% incomparable between spectra: on seven repeat spectra
of one particle, C alone ranges 3.81-15.82 wt%, dragging every other element
with it. Renormalising over alloy elements only collapses Fe's coefficient of
variation from 5.96% to 0.67%.

Both bases are retained. The metal basis drives identification; the as-measured
basis is what the report shows and is needed for the contamination diagnostics.

Stdlib only.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eds_extractor import canonical_element_symbol  # noqa: E402

SIGMA_MODEL_PATH = Path(__file__).resolve().parent / "knowledge" / "sigma_model.json"

#: Elements excluded from the alloy (metal) basis. C/O/N/F are dominated by
#: carbon tape, oxide and mounting medium; Ca/K/Na/Cl/Mg indicate handling or
#: environmental contamination. They are retained as quality signals.
NON_ALLOY_ELEMENTS = frozenset({"C", "O", "N", "F", "Ca", "K", "Na", "Cl", "Mg"})

#: Elements that in THIS domain appear predominantly as a surface treatment
#: rather than as an alloying addition: galvanic/phosphate coatings and
#: precious-metal plating. Whether a given reading is a surface trace or a
#: measured coating layer depends on magnitude, so the decision is made per
#: spectrum rather than statically.
#:
#: Deliberately excluded, despite also occurring in coatings:
#:   Sn, Cu - constituents of the CuSn bronze seal-ring family. Excluding Sn
#:            here removed it from the basis and destroyed the Sn/Cu ratio,
#:            which is the signature that identifies that material.
#:   Ni     - a primary alloying element in austenitic stainless and Ni-base
#:            alloys; it cannot be treated as a coating by default.
#: For elements whose absolute level is unreliable for other reasons, the
#: sigma model's ``prefer_ratio`` flag is the right mechanism, not this list.
COATING_CAPABLE_ELEMENTS = frozenset({"Zn", "P", "Au", "Cd"})

#: Below this share of the ALLOY BASIS (not of the as-measured total), a
#: coating-capable element is treated as a surface trace and kept out of the
#: identification distance.
#:
#: The threshold must be applied on the alloy-relative scale to be meaningful.
#: Testing the as-measured value instead is not scale-invariant: in the bronze
#: particle C+O+F is ~75 wt% of the spectrum, so every metal reading is
#: suppressed ~4x and a 9.6 wt% (alloy-basis) matrix constituent presents as
#: 2.7 wt% as-measured. That is the same closure artefact this module exists to
#: remove.
#:
#: 3.0% sits above the phosphate/galvanic traces in the real reports
#: (Zn 0.23-0.84, P 0.17-0.35 as-measured) and well below a measured coating
#: layer (IC Stud Zn 16.75, NR Nut P 7.63). Provisional: a judgement call,
#: versioned here rather than buried in code.
COATING_TRACE_MAX_BASIS_PCT = 3.0

#: Placeholder strings that mean "not reported" in these sources.
NOT_REPORTED_TOKENS = frozenset(
    {"", "-", "--", ".", "n/a", "na", "nil", "none", "nd", "n.d."}
)


class State(str, Enum):
    """Measurement state of one element in one spectrum."""

    MEASURED = "measured"
    BELOW_LOD = "below_lod"
    NOT_ANALYSED = "not_analysed"


@dataclass
class ElementReading:
    """One element in one spectrum, with its state and uncertainty."""

    element: str
    state: State
    #: As-measured wt% (None unless MEASURED).
    raw_wt: Optional[float] = None
    #: wt% on the alloy basis (None unless MEASURED and an alloy element).
    metal_wt: Optional[float] = None
    #: 1-sigma uncertainty on ``metal_wt``, from the fitted sigma model.
    sigma: Optional[float] = None
    #: Upper bound when BELOW_LOD: the element is somewhere in [0, lod].
    lod: Optional[float] = None
    in_alloy_basis: bool = False
    is_coating_trace: bool = False

    @property
    def informative(self) -> bool:
        """True when this reading can confirm or contradict a grade."""
        return self.state in (State.MEASURED, State.BELOW_LOD)


@dataclass
class NormalizedSpectrum:
    """A canonicalised, dual-basis spectrum ready for scoring."""

    readings: Dict[str, ElementReading] = field(default_factory=dict)
    #: Sum of as-measured wt% over every MEASURED element.
    measured_total: float = 0.0
    #: Sum of as-measured wt% over alloy elements only (pre-renormalisation).
    alloy_total: float = 0.0
    #: Fraction of the measured total that is non-alloy (tape/oxide/handling).
    contamination_fraction: float = 0.0
    #: Fraction of the measured total assigned to the coating channel.
    coating_fraction: float = 0.0
    #: Elements that were part of the analysed set.
    analysed_elements: Tuple[str, ...] = ()
    #: Input keys that could not be resolved to an element symbol.
    unresolved_keys: Tuple[str, ...] = ()
    #: Informational notes that do not impugn the input (e.g. a partial
    #: composition that does not sum to 100, which is a supported input mode).
    warnings: Tuple[str, ...] = ()
    #: Problems that make the INPUT ITSELF suspect: a negative wt%, a value
    #: above 100, a duplicated element key, an unparseable number. Kept
    #: separate from ``warnings`` so the scorer can cap confidence on them
    #: without also penalising legitimately partial input.
    data_quality_errors: Tuple[str, ...] = ()

    # -- accessors -------------------------------------------------------
    def state(self, element: str) -> State:
        r = self.readings.get(element)
        return r.state if r else State.NOT_ANALYSED

    def metal(self, element: str) -> Optional[float]:
        """Alloy-basis wt%, or None if not MEASURED."""
        r = self.readings.get(element)
        return r.metal_wt if r else None

    def sigma(self, element: str) -> Optional[float]:
        r = self.readings.get(element)
        return r.sigma if r else None

    def is_measured(self, element: str) -> bool:
        return self.state(element) is State.MEASURED

    def alloy_elements(self) -> List[str]:
        return [
            e
            for e, r in self.readings.items()
            if r.in_alloy_basis and r.state is State.MEASURED
        ]

    def ratio(self, a: str, b: str) -> Optional[Tuple[float, float]]:
        """Return ``(a/b, sigma)`` on the alloy basis, or None.

        Ratios are the normalisation-invariant part of the signature: any
        residual closure or dilution error cancels, which is why ``Sn/Cu``
        identifies bronze even when absolute Cu is unreliable. Returns None
        unless both terms are MEASURED and the denominator is far enough from
        zero for the ratio to be a constraint rather than a divergence.
        """
        ra, rb = self.readings.get(a), self.readings.get(b)
        if not (ra and rb and ra.state is State.MEASURED and rb.state is State.MEASURED):
            return None
        if not (ra.metal_wt and rb.metal_wt):
            return None
        sa, sb = ra.sigma or 0.0, rb.sigma or 0.0
        # A denominator within 3 sigma of zero makes the ratio unbounded.
        if rb.metal_wt <= 3.0 * sb:
            return None
        value = ra.metal_wt / rb.metal_wt
        rel = math.sqrt((sa / ra.metal_wt) ** 2 + (sb / rb.metal_wt) ** 2)
        return value, value * rel

    def to_dict(self) -> dict:
        return {
            "measured_total": round(self.measured_total, 3),
            "alloy_total": round(self.alloy_total, 3),
            "contamination_fraction": round(self.contamination_fraction, 4),
            "coating_fraction": round(self.coating_fraction, 4),
            "analysed_elements": list(self.analysed_elements),
            "unresolved_keys": list(self.unresolved_keys),
            "warnings": list(self.warnings),
            "data_quality_errors": list(self.data_quality_errors),
            "elements": {
                e: {
                    "state": r.state.value,
                    "raw_wt": r.raw_wt,
                    "metal_wt": None if r.metal_wt is None else round(r.metal_wt, 3),
                    "sigma": None if r.sigma is None else round(r.sigma, 4),
                    "in_alloy_basis": r.in_alloy_basis,
                    "is_coating_trace": r.is_coating_trace,
                }
                for e, r in sorted(self.readings.items())
            },
        }


class SigmaModel:
    """Fitted measurement-uncertainty model, ``sigma(x) = max(floor, cv*x)``."""

    def __init__(self, data: dict):
        self._elements: Dict[str, dict] = data.get("elements", {})
        constants = data.get("constants", {})
        self._default_floor = float(constants.get("sigma_floor_min_wt", 0.05))
        self._default_cv = float(constants.get("cv_fallback", 0.20))
        self._default_lod = float(constants.get("lod_provisional_default_wt", 0.10))
        self.version = data.get("version", "unknown")

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "SigmaModel":
        p = Path(path) if path else SIGMA_MODEL_PATH
        if not p.exists():
            raise FileNotFoundError(
                str(p)
                + " not found. Generate it with:\n"
                + "    python training/derive_sigma_model.py"
            )
        return cls(json.loads(p.read_text(encoding="utf-8")))

    def sigma(self, element: str, value: float) -> float:
        d = self._elements.get(element)
        if not d:
            return max(self._default_floor, self._default_cv * abs(value))
        # cv_scoring, not cv: for heterogeneity-dominated elements the raw
        # observed spread also contains genuine particle-to-particle
        # composition differences, and using it as a measurement sigma yields
        # a tolerance wider than the measurement itself.
        cv = float(d.get("cv_scoring", d.get("cv", self._default_cv)))
        floor = float(d.get("sigma_floor_wt", self._default_floor))
        return max(floor, cv * abs(value))

    def lod(self, element: str) -> float:
        d = self._elements.get(element)
        return float(d.get("lod_wt", self._default_lod)) if d else self._default_lod

    def prefer_ratio(self, element: str) -> bool:
        """True when this element's ABSOLUTE level must not gate identity."""
        d = self._elements.get(element)
        return bool(d.get("prefer_ratio", False)) if d else False

    def is_provisional(self, element: str) -> bool:
        d = self._elements.get(element)
        return bool(d.get("provisional", True)) if d else True


_SIGMA_MODEL: Optional[SigmaModel] = None


def get_sigma_model() -> SigmaModel:
    """Process-wide cached sigma model."""
    global _SIGMA_MODEL
    if _SIGMA_MODEL is None:
        _SIGMA_MODEL = SigmaModel.load()
    return _SIGMA_MODEL


def _coerce(raw: object) -> Tuple[Optional[float], bool]:
    """Return ``(value, was_not_reported)``.

    Distinguishes "explicitly not reported" from "unparseable", so the caller
    can warn about the latter instead of silently treating it as absence.
    """
    if raw is None:
        return None, True
    if isinstance(raw, bool):
        return None, False
    if isinstance(raw, (int, float)):
        v = float(raw)
        return (None, False) if math.isnan(v) or math.isinf(v) else (v, False)
    text = str(raw).strip()
    if text.lower() in NOT_REPORTED_TOKENS:
        return None, True
    try:
        return float(text.replace("%", "").replace(",", "").strip()), False
    except ValueError:
        return None, False


def normalize_spectrum(
    values: Dict[str, object],
    analysed_elements: Optional[Iterable[str]] = None,
    sigma_model: Optional[SigmaModel] = None,
) -> NormalizedSpectrum:
    """Canonicalise one spectrum and compute both bases.

    Args:
        values: element -> wt%. Keys are canonicalised, so ``"FE"``, ``"fe"``
            and ``"Fe%"`` all resolve to ``Fe``. A key whose value is a
            not-reported placeholder is treated as analysed-but-not-detected.
        analysed_elements: the analysed set, i.e. the table's column set. When
            given, an element in this set with no usable value is
            ``BELOW_LOD``, and anything outside it is ``NOT_ANALYSED``. When
            omitted, only the supplied keys are considered analysed - the
            conservative reading for a hand-typed composition.
        sigma_model: override for testing.

    Returns:
        A :class:`NormalizedSpectrum`. Never raises on odd input; problems are
        reported in ``warnings`` and ``unresolved_keys``.
    """
    model = sigma_model or get_sigma_model()
    warnings: List[str] = []
    dq_errors: List[str] = []
    unresolved: List[str] = []

    # -- canonicalise keys ------------------------------------------------
    raw_values: Dict[str, float] = {}
    not_detected: List[str] = []
    for key, raw in values.items():
        element = canonical_element_symbol(str(key))
        if element is None:
            unresolved.append(str(key))
            continue
        value, was_placeholder = _coerce(raw)
        if value is None:
            if was_placeholder:
                not_detected.append(element)
            else:
                unresolved.append(str(key))
                dq_errors.append(
                    "value for " + str(key) + " could not be parsed and was ignored"
                )
            continue
        if value < 0:
            dq_errors.append(
                element + " is negative (" + str(value) + "); treated as not detected"
            )
            not_detected.append(element)
            continue
        if element in raw_values:
            dq_errors.append(
                "duplicate key for " + element + "; keeping the larger value"
            )
            raw_values[element] = max(raw_values[element], value)
        else:
            raw_values[element] = value

    # -- resolve the analysed set ----------------------------------------
    if analysed_elements is None:
        analysed = set(raw_values) | set(not_detected)
    else:
        analysed = set()
        for key in analysed_elements:
            element = canonical_element_symbol(str(key))
            if element:
                analysed.add(element)
        # A value supplied outside the declared column set is still evidence.
        analysed |= set(raw_values) | set(not_detected)

    measured_total = sum(raw_values.values())
    if measured_total > 105.0:
        # A normalised EDS spectrum cannot exceed 100 wt%. This is not a partial
        # composition, it is a bad number.
        dq_errors.append(
            "measured total is "
            + str(round(measured_total, 2))
            + " wt%, which exceeds 100"
        )
    elif 0 < measured_total < 95.0:
        # Legitimate input mode: a caller may supply only the elements of
        # interest. Informational, not an error.
        warnings.append(
            "measured total is "
            + str(round(measured_total, 2))
            + " wt%; treated as a partial composition"
        )

    # -- split the alloy basis from contamination and coating ------------
    # Two passes are required. The coating test is relative to the alloy basis,
    # but the alloy basis is not known until coating traces have been removed.
    # Pass 1 establishes a provisional basis from every alloy candidate; pass 2
    # classifies coating-capable readings against it. A single pass on
    # as-measured values would not be scale-invariant (see
    # COATING_TRACE_MAX_BASIS_PCT).
    candidate_raw = {
        element: value
        for element, value in raw_values.items()
        if element not in NON_ALLOY_ELEMENTS
    }
    candidate_total = sum(candidate_raw.values())

    alloy_raw: Dict[str, float] = {}
    coating_raw: Dict[str, float] = {}
    for element, value in candidate_raw.items():
        if element in COATING_CAPABLE_ELEMENTS and candidate_total > 0:
            basis_pct = value * 100.0 / candidate_total
            if basis_pct <= COATING_TRACE_MAX_BASIS_PCT:
                # A trace of a coating-capable element is a surface signal, not
                # a constituent. Folding it into the basis is what let a
                # 0.84 wt% Zn coating trace pull a plain-carbon-steel particle
                # onto a Zn-bearing reference.
                coating_raw[element] = value
                continue
        alloy_raw[element] = value

    alloy_total = sum(alloy_raw.values())
    coating_total = sum(coating_raw.values())

    # -- build readings ---------------------------------------------------
    readings: Dict[str, ElementReading] = {}
    for element in sorted(analysed):
        if element in raw_values:
            raw_wt = raw_values[element]
            in_basis = element in alloy_raw
            metal_wt = (
                raw_wt * 100.0 / alloy_total if in_basis and alloy_total > 0 else None
            )
            readings[element] = ElementReading(
                element=element,
                state=State.MEASURED,
                raw_wt=raw_wt,
                metal_wt=metal_wt,
                sigma=None if metal_wt is None else model.sigma(element, metal_wt),
                in_alloy_basis=in_basis,
                is_coating_trace=element in coating_raw,
            )
        elif element in not_detected:
            readings[element] = ElementReading(
                element=element,
                state=State.BELOW_LOD,
                lod=model.lod(element),
            )
        else:
            readings[element] = ElementReading(
                element=element, state=State.NOT_ANALYSED
            )

    if alloy_total <= 0 and measured_total > 0:
        warnings.append(
            "no alloy elements measured; composition is entirely "
            "contamination/coating and cannot identify a material"
        )

    return NormalizedSpectrum(
        readings=readings,
        measured_total=measured_total,
        alloy_total=alloy_total,
        contamination_fraction=(
            (measured_total - alloy_total - coating_total) / measured_total
            if measured_total > 0
            else 0.0
        ),
        coating_fraction=coating_total / measured_total if measured_total > 0 else 0.0,
        analysed_elements=tuple(sorted(analysed)),
        unresolved_keys=tuple(unresolved),
        warnings=tuple(warnings),
        data_quality_errors=tuple(dq_errors),
    )


def state_of(
    spectrum: NormalizedSpectrum, element: str, analysed_only: bool = False
) -> State:
    """Convenience wrapper mirroring :meth:`NormalizedSpectrum.state`."""
    state = spectrum.state(element)
    if analysed_only and state is State.NOT_ANALYSED:
        return State.NOT_ANALYSED
    return state
