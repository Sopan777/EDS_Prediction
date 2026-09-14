"""
tests/test_real_particles.py
============================
THE PRIMARY GATE.

Every particle here is real, labelled by an analyst in a Material analysis
report PDF, and transcribed in ``tests/data/real_particles.json`` with its
provenance. These six particles are the only real labelled data that exists,
so they - not synthetic accuracy - decide whether the system works.

Baseline for comparison: the shipped rule engine gets 0 of 5 of these right,
and returns every wrong answer at confidence 1.00.

Two rules govern this file:

1. Accuracy on ``data/synthetic_eds_data.csv`` is never a success criterion.
   That file is the reference table plus jitter (per-class means reproduce the
   reference row to <0.05 wt%, every row sums to exactly 100.000), so measuring
   against it measures memorisation of a lookup table.
2. A confident WRONG answer is a worse failure than an abstention. The tests
   assert that distinction explicitly rather than folding both into "accuracy".
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from backend.ingestion.eds_geometry import available as geometry_available  # noqa: E402
    from backend.ingestion.eds_geometry import extract_tables  # noqa: E402
except ImportError:
    from eds_geometry import available as geometry_available  # noqa: E402
    from eds_geometry import extract_tables  # noqa: E402
from rule_engine.scoring import Decision, predict_particle, predict_spectrum  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "data" / "real_particles.json"

#: Expected family PREFIX per particle. A prefix, because the sub-family split
#: (F6a bronze vs F6b bronze-on-steel, F8a Zn vs F8b Zn-phosphate) is a
#: reporting refinement - either is a correct material call.
#: ``None`` means abstention is the correct answer: the report itself assigns
#: no chemistry to that site.
EXPECTED_FAMILY = {
    "26-108-site1": "F1a",
    "26-108-site2": "F1b",
    "26-130-site1": "F1b",
    "26-130-site2": "F1b",
    "26-130-site4-ball": None,
    "26-146": "F6",
}


def _load():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["particles"]


PARTICLES = _load()
PARTICLE_IDS = [p["id"] for p in PARTICLES]


@pytest.fixture(scope="module")
def particles():
    return {p["id"]: p for p in _load()}


# ---------------------------------------------------------------------------
# Fixture integrity - the truth set must stay faithful to the PDFs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("pid", PARTICLE_IDS)
def test_fixture_spectra_are_normalised(particles, pid):
    """Each spectrum is 'All elements analysed (Normalised)', so it sums to ~100."""
    for spectrum in particles[pid]["spectra"]:
        total = sum(spectrum["values"].values())
        assert 98.5 <= total <= 101.5, (
            pid + " spectrum " + spectrum["spectrum"] + " sums to " + str(total)
        )


@pytest.mark.parametrize("pid", PARTICLE_IDS)
def test_fixture_never_encodes_absence_as_zero(particles, pid):
    """A not-measured element must be OMITTED, never recorded as 0.0.

    Encoding absence as zero is the defect this whole rebuild exists to remove;
    the truth set must not reintroduce it.
    """
    for spectrum in particles[pid]["spectra"]:
        zeros = [e for e, v in spectrum["values"].items() if v == 0.0]
        assert not zeros, pid + " encodes absence as zero for " + str(zeros)


@pytest.mark.parametrize("pid", PARTICLE_IDS)
def test_fixture_rows_account_for_declared_columns(particles, pid):
    """values + not_measured must be exactly the table's column set."""
    declared = set(particles[pid]["table_columns"])
    for spectrum in particles[pid]["spectra"]:
        got = set(spectrum["values"]) | set(spectrum["not_measured"])
        assert got == declared, (
            pid + " spectrum " + spectrum["spectrum"] + " covers " + str(sorted(got))
        )


# ---------------------------------------------------------------------------
# The gate itself
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("pid", PARTICLE_IDS)
def test_particle_family_is_correct_or_abstains(particles, pid):
    """The material family must be right, or the engine must decline to answer."""
    particle = particles[pid]
    expected = EXPECTED_FAMILY[pid]
    prediction = predict_particle(
        [s["values"] for s in particle["spectra"]],
        analysed_elements=particle["table_columns"],
    )

    if expected is None:
        assert prediction.decision in (Decision.UNKNOWN, Decision.AMBIGUOUS), (
            pid
            + ": report assigns no chemistry, so a confident single answer is wrong "
            + "(got " + str(prediction.decision.value) + ")"
        )
        return

    assert prediction.decision is not Decision.UNKNOWN, (
        pid + ": expected " + expected + ", got an abstention: " + prediction.reason
    )
    assert prediction.top is not None
    assert prediction.top.family_id.startswith(expected), (
        pid
        + ": expected family "
        + expected
        + "*, got "
        + prediction.top.family_id
        + " ("
        + prediction.top.label
        + ")"
    )


@pytest.mark.parametrize("pid", PARTICLE_IDS)
def test_no_confidently_wrong_answer(particles, pid):
    """No particle may receive a high-compatibility answer for the wrong family.

    This is the metric that matters most: the shipped engine's failure mode was
    not low accuracy, it was certainty while wrong.
    """
    particle = particles[pid]
    expected = EXPECTED_FAMILY[pid]
    prediction = predict_particle(
        [s["values"] for s in particle["spectra"]],
        analysed_elements=particle["table_columns"],
    )
    if prediction.top is None:
        return
    if expected is not None and prediction.top.family_id.startswith(expected):
        return
    assert prediction.top.compatibility < 0.5, (
        pid
        + ": reported "
        + prediction.top.label
        + " at compatibility "
        + str(round(prediction.top.compatibility, 3))
        + " but the correct family is "
        + str(expected)
    )


def test_whole_truth_set_passes(particles):
    """Aggregate gate, so a regression cannot hide behind a single case."""
    correct = []
    wrong = []
    for pid, particle in particles.items():
        expected = EXPECTED_FAMILY[pid]
        prediction = predict_particle(
            [s["values"] for s in particle["spectra"]],
            analysed_elements=particle["table_columns"],
        )
        fid = prediction.top.family_id if prediction.top else None
        if expected is None:
            ok = prediction.decision in (Decision.UNKNOWN, Decision.AMBIGUOUS)
        else:
            ok = bool(fid and fid.startswith(expected))
        (correct if ok else wrong).append(pid)
    assert not wrong, "failed particles: " + str(wrong)
    assert len(correct) == len(EXPECTED_FAMILY)


def test_compatibility_is_never_certainty(particles):
    """Compatibility is a goodness-of-fit statistic, not a probability.

    The old engine reported 1.00 on answers that were chemically impossible.
    Nothing may report certainty.
    """
    for pid, particle in particles.items():
        prediction = predict_particle(
            [s["values"] for s in particle["spectra"]],
            analysed_elements=particle["table_columns"],
        )
        for family in prediction.families:
            assert family.compatibility < 1.0, pid + " reported certainty"


def test_ambiguity_is_reported_as_a_set(particles):
    """Where the analyst wrote '??', an ambiguous set is a legitimate answer."""
    particle = particles["26-130-site1"]
    assert particle["analyst_uncertain"] is True
    prediction = predict_particle(
        [s["values"] for s in particle["spectra"]],
        analysed_elements=particle["table_columns"],
    )
    # More than one component shares this family, so the candidate list must
    # not collapse to a single confident source.
    assert len(prediction.candidate_components) > 1


def test_abstention_lists_no_candidates(particles):
    """An abstention must not hand over a shortlist it cannot support."""
    for pid, particle in particles.items():
        prediction = predict_particle(
            [s["values"] for s in particle["spectra"]],
            analysed_elements=particle["table_columns"],
        )
        if prediction.decision is Decision.UNKNOWN:
            assert prediction.candidate_components == []
            assert prediction.to_dict()["material_family"] is None


def test_carbon_caveat_always_present(particles):
    """EDS cannot quantify carbon, so no answer may imply a carbon grade."""
    for pid, particle in particles.items():
        prediction = predict_particle(
            [s["values"] for s in particle["spectra"]],
            analysed_elements=particle["table_columns"],
        )
        assert any("arbon" in c for c in prediction.caveats), pid


# ---------------------------------------------------------------------------
# End to end: PDF file -> answer, with no hand-entered data
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not geometry_available(), reason="PyMuPDF not installed")
@pytest.mark.parametrize("pid", PARTICLE_IDS)
def test_extraction_reproduces_the_truth_set(particles, pid):
    """The geometry extractor must reproduce the hand-verified values exactly.

    The text-based extractor could not: it read the 26-146 table as ['O','F']
    with every value None, because narrow columns are separated by a single
    space and the numerals are not aligned to the header's character offsets.
    """
    particle = particles[pid]
    pdf = ROOT / "data" / "reports" / particle["source_pdf"]
    if not pdf.exists():
        pdf = ROOT / particle["source_pdf"]
    if not pdf.exists():  # tolerate the odd whitespace in these filenames
        tag = particle["complaint_no"].replace("CRI.I. ", "")
        candidates = list((ROOT / "data" / "reports").glob("*.pdf")) + list(ROOT.glob("*.pdf"))
        matches = [p for p in candidates if tag in p.name]
        assert matches, "no PDF found for " + tag
        pdf = matches[0]

    tables = extract_tables(str(pdf))["eds_tables"]
    page_tables = [t for t in tables if t["page"] == particle["pdf_page"]]
    assert page_tables, pid + ": no table found on page " + str(particle["pdf_page"])
    table = page_tables[0]

    assert set(table["elements"]) - {"Total"} == set(particle["table_columns"])

    by_id = {s["spectrum"]: s["values"] for s in table["spectra"]}
    for spectrum in particle["spectra"]:
        got = by_id.get(spectrum["spectrum"])
        assert got is not None, pid + " missing spectrum " + spectrum["spectrum"]
        for element, expected_value in spectrum["values"].items():
            assert got.get(element) == pytest.approx(expected_value), (
                pid + " " + element
            )
        for element in spectrum["not_measured"]:
            assert got.get(element) is None, (
                pid
                + " "
                + element
                + " was blank in the PDF and must extract as None, not 0.0"
            )


@pytest.mark.skipif(not geometry_available(), reason="PyMuPDF not installed")
def test_end_to_end_pdf_to_family(particles):
    """Full path: PDF -> extract -> normalise -> score, no hand-entered data."""
    checked = 0
    for pid, particle in particles.items():
        expected = EXPECTED_FAMILY[pid]
        if expected is None:
            continue
        tag = particle["complaint_no"].replace("CRI.I. ", "")
        candidates = list((ROOT / "data" / "reports").glob("*.pdf")) + list(ROOT.glob("*.pdf"))
        matches = [p for p in candidates if tag in p.name]
        if not matches:
            continue
        tables = [
            t
            for t in extract_tables(str(matches[0]))["eds_tables"]
            if t["page"] == particle["pdf_page"]
        ]
        if not tables:
            continue
        table = tables[0]
        columns = [e for e in table["elements"] if e != "Total"]
        spectra = [
            {k: v for k, v in s["values"].items() if v is not None and k != "Total"}
            for s in table["spectra"]
        ]
        prediction = predict_particle(spectra, analysed_elements=columns)
        assert prediction.top is not None, pid + " abstained end to end"
        assert prediction.top.family_id.startswith(expected), (
            pid + " end to end got " + prediction.top.family_id
        )
        checked += 1
    assert checked >= 4, "expected at least 4 end-to-end particles, got " + str(checked)
