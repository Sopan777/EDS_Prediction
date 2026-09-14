"""
training/validate_loco.py
=========================
Leave-one-component-out validation. The honest generalisation test.

What this measures, and why it is not circular
----------------------------------------------
Predicting the spectra a band was derived from proves nothing. So for each
component in turn this script:

1. removes ALL of that component's spectra,
2. rebuilds the element bands from the remaining components only,
3. predicts the held-out spectra against those bands.

The question it answers is therefore: *do bands derived from the OTHER members
of a family still accept a member they have never seen?* That is generalisation.

Ground truth, and a correction
------------------------------
An earlier version of this harness used each component's majority family as the
label. That is wrong, and the data says so: ``M&M HPP Component`` has spectra at
Fe ~96% (steel) on sites 1-3 and Zn ~93% (coating) on sites 4-5, and
``Blade Terminal`` has one spectrum at Au 88% and another at Cu ~48%. Scoring
the coating spectra against a "steel" label counted correct answers as errors.

The truth label is therefore per SPECTRUM, taken from the metallurgical
predicate - which is standing domain knowledge, not fitted to these bands. The
predicate is never rebuilt during the sweep, only the bands are, so this remains
a test of the bands.

Metrics are reported at family and component level SEPARATELY, never averaged:
component-level top-1 is not a target, because 20 of 630 component pairs are
indistinguishable at 3 sigma and every one of those collisions is inside a
single family.

Accuracy on ``data/synthetic_eds_data.csv`` is deliberately not reported: that
file is the reference table plus jitter, so any score on it is circular.
"""

from __future__ import annotations

import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rule_engine.normalize import get_sigma_model, normalize_spectrum  # noqa: E402
from rule_engine.real_data import (  # noqa: E402
    group_by_component,
    is_surface_treatment,
    load_spectra,
)
from rule_engine.scoring import (  # noqa: E402
    Decision,
    KnowledgeBase,
    Verdict,
    predict_spectrum,
    score_family,
)
from training.derive_knowledge import (  # noqa: E402
    BAND_WIDEN_SIGMA,
    FAMILY_DEFS,
    FAMILY_RATIOS,
    MIN_SPECTRA_FOR_BAND,
    assign_families,
)


def _records() -> List[dict]:
    """Every real spectrum, normalised, with its predicate family label."""
    out: List[dict] = []
    for s in load_spectra():
        ns = normalize_spectrum(s.values, analysed_elements=list(s.values))
        metal = {e: ns.metal(e) for e in ns.alloy_elements()}
        if not metal:
            continue
        out.append(
            {
                "component": s.component,
                "row": s.row,
                "values": dict(s.values),
                "analysed": list(s.values),
                "metal": metal,
                "truth_families": assign_families(metal),
                "surface_variant": is_surface_treatment(s.component),
            }
        )
    return out


def _build_kb(records: List[dict]) -> KnowledgeBase:
    """Rebuild the knowledge base from the supplied records only."""
    sigma_model = get_sigma_model()
    families: Dict[str, dict] = {}
    for fam in FAMILY_DEFS:
        fid = fam["id"]
        members = [r for r in records if fid in r["truth_families"]]
        by_element: Dict[str, List[float]] = {}
        for r in members:
            for element, value in r["metal"].items():
                by_element.setdefault(element, []).append(value)

        elements: Dict[str, dict] = {}
        for element, values in by_element.items():
            mean = st.mean(values)
            sigma = sigma_model.sigma(element, mean)
            elements[element] = {
                "band_wt": [
                    max(0.0, round(min(values) - BAND_WIDEN_SIGMA * sigma, 3)),
                    round(max(values) + BAND_WIDEN_SIGMA * sigma, 3),
                ],
                "n_spectra": len(values),
                "required": len(values) == len(members) and mean > 0.3,
                "provisional": len(values) < MIN_SPECTRA_FOR_BAND,
                "prefer_ratio": sigma_model.prefer_ratio(element),
            }

        real_components = sorted(
            {r["component"] for r in members if not r["surface_variant"]}
        )
        families[fid] = {
            "label": fam["label"],
            "grade_hint": fam["grade_hint"],
            "discriminators": fam["discriminators"],
            "ratios": FAMILY_RATIOS.get(fid, []),
            "elements": elements,
            "components": real_components,
            "n_spectra": len(members),
            "provisional": len(real_components) < 2,
        }
    return KnowledgeBase({"version": "loco", "families": families, "components": {}})


def _leave_one_spectrum_out(records: List[dict]) -> dict:
    """Component-level retrieval, holding out one SPECTRUM at a time.

    The component keeps its other spectra, so the reference still knows it
    exists. This is the setting in which "is the true component in the
    candidate list?" is a real question - and it is reported as recall over a
    LIST, never as top-1, because component identity is not recoverable from
    EDS composition alone.
    """
    answered = 0
    in_list = 0
    list_sizes: List[int] = []
    for i, held in enumerate(records):
        kept = [r for j, r in enumerate(records) if j != i]
        kb = _build_kb(kept)
        prediction = predict_spectrum(
            held["values"], analysed_elements=held["analysed"], knowledge=kb
        )
        if prediction.decision is Decision.UNKNOWN:
            continue
        answered += 1
        candidates = prediction.candidate_components
        list_sizes.append(len(candidates))
        if held["component"] in candidates:
            in_list += 1
    return {
        "answered": answered,
        "component_in_candidate_list": in_list,
        "recall": round(in_list / answered, 4) if answered else 0.0,
        "median_candidate_list_size": (
            st.median(list_sizes) if list_sizes else 0
        ),
    }


def run() -> dict:
    records = _records()
    components = sorted({r["component"] for r in records})

    rows: List[dict] = []
    for held in components:
        kept = [r for r in records if r["component"] != held]
        held_out = [r for r in records if r["component"] == held]
        kb = _build_kb(kept)

        for r in held_out:
            prediction = predict_spectrum(
                r["values"], analysed_elements=r["analysed"], knowledge=kb
            )
            reported = (
                [f.family_id for f in prediction.families]
                if prediction.decision is Decision.AMBIGUOUS
                else ([prediction.top.family_id] if prediction.top else [])
            )
            truth = r["truth_families"]
            rows.append(
                {
                    "component": held,
                    "row": r["row"],
                    "truth": truth,
                    "decision": prediction.decision.value,
                    "reported": reported,
                    "family_hit": bool(set(reported) & set(truth)),
                    "component_in_candidates": held in prediction.candidate_components,
                    "reason": prediction.reason,
                    "compatibility": (
                        prediction.top.compatibility if prediction.top else 0.0
                    ),
                    "n_candidates": len(prediction.candidate_components),
                }
            )

    evaluated = [r for r in rows if r["decision"] != "unknown"]
    abstained = [r for r in rows if r["decision"] == "unknown"]
    hits = [r for r in evaluated if r["family_hit"]]
    misses = [r for r in evaluated if not r["family_hit"]]
    # A confident wrong answer is the failure that matters most.
    confident_wrong = [r for r in misses if r["compatibility"] >= 0.5]
    # Component recall is NOT measurable under leave-one-COMPONENT-out: the
    # held-out component is absent from the rebuilt reference, so it can never
    # appear in its own candidate list. Measuring it there yields a tautological
    # 0%. The meaningful question - "when the reference DOES contain the
    # component, is it retrieved?" - needs leave-one-SPECTRUM-out, below.
    recall = [r for r in evaluated if r["component_in_candidates"]]

    return {
        "n_spectra": len(rows),
        "n_evaluated": len(evaluated),
        "n_abstained": len(abstained),
        "family_hits": len(hits),
        "family_misses": len(misses),
        "confident_wrong": len(confident_wrong),
        "component_recall_in_candidates": len(recall),
        "component_recall_measurable": False,
        "loso": _leave_one_spectrum_out(records),
        "rows": rows,
        "misses": misses,
        "confident_wrong_rows": confident_wrong,
    }


def main() -> None:
    report = run()
    n, ev = report["n_spectra"], report["n_evaluated"]

    print("=" * 72)
    print("LEAVE-ONE-COMPONENT-OUT: bands rebuilt without the held-out component")
    print("=" * 72)
    print("  real spectra swept        : " + str(n))
    print(
        "  answered                  : "
        + str(ev)
        + "  ("
        + str(round(ev / n * 100, 1))
        + "%)"
    )
    print(
        "  abstained                 : "
        + str(report["n_abstained"])
        + "  ("
        + str(round(report["n_abstained"] / n * 100, 1))
        + "%)"
    )
    print("")
    print("  FAMILY level (the target):")
    if ev:
        print(
            "    correct                 : "
            + str(report["family_hits"])
            + "/"
            + str(ev)
            + "  ("
            + str(round(report["family_hits"] / ev * 100, 1))
            + "% of answered)"
        )
        print(
            "    wrong                   : "
            + str(report["family_misses"])
            + "  of which CONFIDENTLY wrong: "
            + str(report["confident_wrong"])
        )
        print("")
        print("  COMPONENT level (not a target - see module docstring):")
        print(
            "    under LOCO              : not measurable by construction "
            "(held-out component is absent from the reference)"
        )
        loso = report["loso"]
        print(
            "    leave-one-SPECTRUM-out  : "
            + str(loso["component_in_candidate_list"])
            + "/"
            + str(loso["answered"])
            + " recall ("
            + str(round(loso["recall"] * 100, 1))
            + "%), median list size "
            + str(loso["median_candidate_list_size"])
        )

    if report["misses"]:
        print("")
        print("  family misses:")
        for m in report["misses"][:15]:
            print(
                "    "
                + (m["component"][:26]).ljust(28)
                + "r"
                + str(m["row"]).ljust(5)
                + "truth="
                + str(m["truth"])
                + " got="
                + str(m["reported"])
                + " comp="
                + str(round(m["compatibility"], 2))
            )

    print("")
    print("  abstention causes:")
    def _bucket(reason: str) -> str:
        for key in (
            "insufficient metal signal",
            "insufficient evidence",
            "no material fits well enough",
            "out of reference",
        ):
            if key in reason:
                return key
        return reason[:40]

    causes = Counter(
        _bucket(r.get("reason", ""))
        for r in report["rows"]
        if r["decision"] == "unknown"
    )
    for cause, count in causes.items():
        print("    " + cause.ljust(26) + str(count))

    out = Path(__file__).resolve().parent.parent / "outputs" / "loco_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("")
    print("  wrote " + str(out))


if __name__ == "__main__":
    main()
