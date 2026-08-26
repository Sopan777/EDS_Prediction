"""
tests/test_scoring_invariance.py
================================
Property, invariance and negative-control tests for the scoring engine.

These tests need no labels, which is what makes them valuable when only six
real labelled particles exist. They assert structural properties that must hold
for any input:

* **Invariance** - the metal basis must make identification independent of how
  much carbon tape, oxide or mounting medium landed in the spectrum. This is the
  direct test of the highest-leverage preprocessing fix.
* **Negative controls** - a composition with no support must be refused. The old
  engine's defining failure was not low accuracy, it was certainty while wrong:
  ``{S: 0.2}`` returned "Guide Bush" at confidence 1.00 for a material whose
  every reference spectrum carries 1.12-1.60 wt% Mn.
* **Three-state missingness** - an element that was never analysed must never
  satisfy a constraint, and must be distinguishable from one analysed and found
  absent.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rule_engine.normalize import State, normalize_spectrum  # noqa: E402
from rule_engine.scoring import (  # noqa: E402
    MAX_COMPATIBILITY,
    Decision,
    predict_particle,
    predict_spectrum,
)

#: A clean 1.5Mn steel, on the alloy basis.
MN_STEEL = {"Si": 0.40, "Mn": 1.40, "Fe": 88.0}

#: A clean 100Cr6-family bearing steel.
CR_STEEL = {"Si": 0.35, "Cr": 1.70, "Mn": 0.30, "Fe": 93.0}


def _with_contamination(base: dict, c_plus_o_pct: float) -> dict:
    """Rescale ``base`` so C+O occupy the given share, then close to 100%."""
    scale = (100.0 - c_plus_o_pct) / sum(base.values())
    out = {k: round(v * scale, 4) for k, v in base.items()}
    out["C"] = round(c_plus_o_pct * 0.8, 4)
    out["O"] = round(c_plus_o_pct * 0.2, 4)
    return out


# ---------------------------------------------------------------------------
# Invariance to specimen-preparation contamination
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("contamination", [0.0, 5.0, 12.0, 25.0, 45.0, 60.0])
def test_metal_basis_is_invariant_to_contamination(contamination):
    """Metal-basis values must not move as C+O grows.

    On seven repeat spectra of one real particle, C alone ranges 3.81-15.82 wt%,
    dragging every other element with it under the sum-to-100 closure.
    """
    spectrum = normalize_spectrum(_with_contamination(MN_STEEL, contamination))
    assert spectrum.metal("Mn") == pytest.approx(1.559, abs=0.01)
    assert spectrum.metal("Si") == pytest.approx(0.445, abs=0.01)
    assert spectrum.metal("Fe") == pytest.approx(97.996, abs=0.05)


@pytest.mark.parametrize("contamination", [0.0, 10.0, 30.0, 55.0])
def test_family_prediction_is_invariant_to_contamination(contamination):
    """The identified family must not change with contamination level."""
    values = _with_contamination(MN_STEEL, contamination)
    prediction = predict_spectrum(values, analysed_elements=list(values))
    assert prediction.decision is Decision.IDENTIFIED
    assert prediction.top is not None
    assert prediction.top.family_id == "F1b"


def test_contamination_is_reported_not_hidden():
    """Contamination fraction must surface as a quality signal."""
    heavy = _with_contamination(MN_STEEL, 55.0)
    prediction = predict_spectrum(heavy, analysed_elements=list(heavy))
    assert prediction.quality["contamination_fraction"] > 0.5


def test_scale_invariance():
    """Rescaling to a valid EDS total must not change the identified family.

    The metal basis renormalises internally, so only proportions should
    matter. The scale factor is chosen to land the total within the range a
    real normalised EDS spectrum can plausibly report (~95-105 wt%):
    doubling CR_STEEL instead pushes its total to ~190.7 wt%, which correctly
    trips the data-quality total-over-100 guard and caps confidence. That was
    a defect in the test, not the scorer - an EDS total of 191% is not a
    legitimate input to demand invariance over.
    """
    scale = 100.0 / sum(CR_STEEL.values())
    rescaled = {k: v * scale for k, v in CR_STEEL.items()}
    a = predict_spectrum(CR_STEEL, analysed_elements=list(CR_STEEL))
    b = predict_spectrum(rescaled, analysed_elements=list(rescaled))
    assert a.top is not None and b.top is not None
    assert a.top.family_id == b.top.family_id
    assert a.top.compatibility == pytest.approx(b.top.compatibility, abs=0.01)


def test_element_order_invariance():
    """A dict is unordered in meaning; results must not depend on key order."""
    reversed_keys = dict(reversed(list(CR_STEEL.items())))
    a = predict_spectrum(CR_STEEL, analysed_elements=list(CR_STEEL))
    b = predict_spectrum(reversed_keys, analysed_elements=list(reversed_keys))
    assert a.top.family_id == b.top.family_id
    assert a.top.compatibility == pytest.approx(b.top.compatibility)


# ---------------------------------------------------------------------------
# Element-name canonicalisation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "keys",
    [
        {"FE": 88.0, "MN": 1.40, "SI": 0.40},
        {"fe": 88.0, "mn": 1.40, "si": 0.40},
        {"Fe%": 88.0, "Mn ": 1.40, " Si": 0.40},
        {"Fe(wt%)": 88.0, "Mn(wt%)": 1.40, "Si(wt%)": 0.40},
    ],
)
def test_case_and_annotation_variants_resolve(keys):
    """``FE``, ``fe``, ``Fe%`` and ``Fe(wt%)`` must all reach the same answer.

    Previously only the exact training spelling matched; anything else silently
    scored as an all-zero vector and produced a confident wrong answer.
    """
    prediction = predict_spectrum(keys, analysed_elements=list(keys))
    assert prediction.top is not None
    assert prediction.top.family_id == "F1b"


def test_unknown_symbols_are_rejected_not_coerced():
    """An unrecognised key must be reported, never silently treated as absent."""
    spectrum = normalize_spectrum({"Xx": 50.0, "Fe": 50.0})
    assert "Xx" in spectrum.unresolved_keys


def test_oxide_formulae_are_rejected():
    """``Al2O3`` wt% is not ``Al`` wt%, so it must not be read as the element."""
    spectrum = normalize_spectrum({"Al2O3": 30.0, "Fe": 70.0})
    assert "Al2O3" in spectrum.unresolved_keys
    assert spectrum.state("Al") is State.NOT_ANALYSED


# ---------------------------------------------------------------------------
# Three-state missingness
# ---------------------------------------------------------------------------


def test_not_analysed_differs_from_below_lod():
    """The two absences are different evidence and must not collapse."""
    not_analysed = normalize_spectrum({"Fe": 98.0, "Mn": 1.4})
    below_lod = normalize_spectrum(
        {"Fe": 98.0, "Mn": 1.4, "Cr": "-"}, analysed_elements=["Fe", "Mn", "Cr"]
    )
    assert not_analysed.state("Cr") is State.NOT_ANALYSED
    assert below_lod.state("Cr") is State.BELOW_LOD


@pytest.mark.parametrize("placeholder", ["-", "", "n/a", "N/A", "nil", None])
def test_placeholders_mean_below_lod_not_zero(placeholder):
    """A placeholder means "analysed, not detected" - never a measured 0.0."""
    spectrum = normalize_spectrum(
        {"Fe": 98.0, "Mn": 1.4, "Cr": placeholder},
        analysed_elements=["Fe", "Mn", "Cr"],
    )
    assert spectrum.state("Cr") is State.BELOW_LOD
    assert spectrum.metal("Cr") is None


def test_unanalysed_element_cannot_confirm_a_family():
    """An austenitic grade needs Cr AND Ni measured; absence must not pass.

    This is the 26-108-site2 failure: a plain 1.5Mn steel was reported as
    "Magnet housing" (X8CrNiS18-9, Cr~17.8/Ni~8.1) at confidence 1.00 by a rule
    that never checked Cr or Ni.
    """
    prediction = predict_spectrum(
        {"Si": 0.39, "Mn": 1.42, "Fe": 88.0}, analysed_elements=["Si", "Mn", "Fe"]
    )
    assert prediction.top is not None
    assert prediction.top.family_id != "F4"
    austenitic = [f for f in prediction.families if f.family_id == "F4"]
    if austenitic:
        assert austenitic[0].compatibility == 0.0


# ---------------------------------------------------------------------------
# Negative controls - must refuse rather than guess
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label,values",
    [
        ("the reported Mn bug", {"S": 0.2}),
        ("single trace Ni", {"Ni": 0.3}),
        ("single trace Si", {"Si": 0.14}),
        ("empty spectrum", {}),
        ("aluminium only", {"Al": 99.0}),
        ("titanium alloy, out of reference", {"Ti": 90.0, "Al": 6.0, "V": 4.0}),
        ("polymer, no metal", {"C": 60.0, "O": 38.0, "F": 2.0}),
        ("implausible Mn", {"Fe": 90.0, "Mn": 8.0, "Si": 0.3}),
        ("implausible Cr", {"Fe": 68.0, "Cr": 30.0, "Ni": 1.0}),
        ("unknown symbol only", {"Xx": 99.0}),
    ],
)
def test_unsupported_compositions_abstain(label, values):
    """No family may be asserted for a composition nothing supports."""
    prediction = predict_spectrum(
        values, analysed_elements=list(values) if values else None
    )
    assert prediction.decision is Decision.UNKNOWN, (
        label + ": expected abstention, got " + prediction.decision.value
    )
    assert prediction.top is None
    assert prediction.candidate_components == []
    assert prediction.reason


def test_the_reported_bug_stays_fixed():
    """Regression test for the exact failure that prompted this work.

    ``{S: 0.2}`` returned "Guide Bush" at confidence 1.00 - a material whose
    every reference spectrum contains 1.12-1.60 wt% Mn - because Mn was absent
    (coerced to 0.0) and the rule's Mn lower bound had been pruned away.
    """
    prediction = predict_spectrum({"S": 0.2}, analysed_elements=["S"])
    assert prediction.decision is Decision.UNKNOWN
    assert "Guide Bush" not in prediction.candidate_components


def test_low_mn_never_yields_a_high_mn_material():
    """Generalised form: Mn far below a family's band must exclude it."""
    prediction = predict_spectrum(
        {"Fe": 99.2, "Mn": 0.10, "Si": 0.3}, analysed_elements=["Fe", "Mn", "Si"]
    )
    if prediction.top is not None:
        assert prediction.top.family_id != "F1b"
    high_mn = [f for f in prediction.families if f.family_id == "F1b"]
    if high_mn:
        assert high_mn[0].compatibility < 0.5


# ---------------------------------------------------------------------------
# Confidence semantics and data quality
# ---------------------------------------------------------------------------


def test_compatibility_is_never_one():
    """Compatibility is goodness of fit, not probability; certainty is barred."""
    prediction = predict_spectrum(CR_STEEL, analysed_elements=list(CR_STEEL))
    assert prediction.top is not None
    assert prediction.top.compatibility <= MAX_COMPATIBILITY < 1.0


def test_compatibility_varies_with_fit():
    """Two different inputs must not receive identical confidence.

    The retired engine returned a constant frozen at training time, so a
    spectrum at the edge of every band scored exactly the same as one at the
    centre.
    """
    centre = predict_spectrum(CR_STEEL, analysed_elements=list(CR_STEEL))
    edge = predict_spectrum(
        {"Si": 0.35, "Cr": 3.6, "Mn": 0.30, "Fe": 93.0},
        analysed_elements=["Si", "Cr", "Mn", "Fe"],
    )
    assert centre.top is not None
    if edge.top is not None:
        assert centre.top.compatibility != pytest.approx(edge.top.compatibility)


@pytest.mark.parametrize(
    "label,values",
    [
        ("negative wt%", {"Fe": 95.0, "Cr": -5.0, "Mn": 0.5}),
        ("total above 100", {"Fe": 9999.0, "Cr": 1.5}),
        ("duplicate key", {"Fe": 95.0, "Fe%": 94.0, "Mn": 1.4}),
    ],
)
def test_bad_input_caps_confidence(label, values):
    """Suspect input may still be identifiable, but never at full confidence."""
    prediction = predict_spectrum(values, analysed_elements=list(values))
    if prediction.top is not None:
        assert prediction.top.compatibility <= 0.45, label
    assert any("quality" in c for c in prediction.caveats), label


def test_partial_composition_is_not_a_data_error():
    """Supplying only the elements of interest is legitimate, not an error."""
    spectrum = normalize_spectrum({"Cr": 1.7, "Mn": 0.3})
    assert spectrum.data_quality_errors == ()


# ---------------------------------------------------------------------------
# Multi-spectrum pooling
# ---------------------------------------------------------------------------


def test_pooling_rejects_a_family_contradicted_by_any_spectrum():
    """Evidence is pooled, not voted: one contradiction disqualifies a family.

    The retired roll-up took a majority vote, so a minority of spectra carrying
    decisive counter-evidence could be outvoted.
    """
    spectra = [
        {"Si": 0.40, "Mn": 1.40, "Fe": 88.0},
        {"Si": 0.40, "Mn": 1.45, "Fe": 88.0},
        {"Si": 0.40, "Cr": 18.0, "Ni": 9.0, "Mn": 1.4, "Fe": 70.0},
    ]
    prediction = predict_particle(spectra)
    reported = [f.family_id for f in prediction.families]
    assert "F1b" not in reported or prediction.decision is not Decision.IDENTIFIED


def test_pooling_agrees_with_a_single_consistent_spectrum():
    """Repeat measurements of one material must not change the family."""
    single = predict_spectrum(MN_STEEL, analysed_elements=list(MN_STEEL))
    pooled = predict_particle([MN_STEEL, dict(MN_STEEL), dict(MN_STEEL)])
    assert single.top is not None and pooled.top is not None
    assert single.top.family_id == pooled.top.family_id


def test_empty_particle_abstains():
    assert predict_particle([]).decision is Decision.UNKNOWN
