"""
training/derive_sigma_model.py
==============================
Derive the EDS measurement-uncertainty model from REAL repeat spectra.

Why this exists
---------------
Every tolerance in the prediction engine needs a sigma. Inventing those
numbers is exactly what the audit warned against, so they are fitted here
from the only real multi-spectrum data available: the ``Components`` sheet of
``data/EDS Consolidation.xlsx`` (173 spectra, 43 labels, median 4 per label).

Two facts drive the model shape
-------------------------------
1. Sigma is NOT constant per element. Measured on the real spectra, the
   median within-group scatter is ~0.08 wt% below 2 wt% but ~0.34 wt% above
   20 wt%, while the coefficient of variation is the stabler description.
   So::

       sigma_e(x) = max(floor_e, cv_e * x)

2. There are two different variances, and they answer different questions:

   * within-PARTICLE  - repeat spectra of one particle (instrument noise).
   * within-COMPONENT - spectra of the same component across different
     particles, sites and surface preparations.

   For "could this NEW particle be this component?" the second is the honest,
   conservative choice, because a new particle differs from the reference in
   all the same ways. This script fits the within-COMPONENT variance.

   Using within-particle noise instead makes thresholds look far sharper than
   they are: the F1a/F1b manganese boundary is ~4.7 sigma on within-particle
   noise but only ~1.7 sigma on within-component scatter.

Output
------
``rule_engine/knowledge/sigma_model.json``, carrying provenance and an
explicit ``provisional`` flag on any value not supported by enough data.

Stdlib only.
"""

from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rule_engine.real_data import (  # noqa: E402
    group_by_component,
    is_surface_treatment,
    load_spectra,
)

OUT_PATH = (
    Path(__file__).resolve().parent.parent
    / "rule_engine"
    / "knowledge"
    / "sigma_model.json"
)

#: Elements excluded from the metal basis (specimen preparation, not material).
#: C/O/N/F come largely from carbon tape, oxide and mounting medium.
NON_ALLOY = {"C", "O", "N", "F", "Ca", "K", "Cl"}

#: Minimum groups (components with >=3 spectra) needed to trust a fitted value.
MIN_GROUPS = 3

#: Below this concentration a value is treated as the "low" regime used to fit
#: the additive floor.
LOW_CONC_WT = 2.0

#: Absolute floor on sigma_floor, in wt%. Standardless EDS repeatability does
#: not meaningfully beat this, and letting a fitted floor collapse toward zero
#: would manufacture false precision for elements that happened to be stable
#: across a handful of spectra.
SIGMA_FLOOR_MIN = 0.05

#: Provisional per-element limit of detection, wt%. NOT fitted - standardless
#: EDS is typically 0.1-0.5 wt% depending on element and acquisition. Flagged
#: provisional: it must be confirmed against the actual instrument before any
#: "element is absent" conclusion is treated as hard evidence.
LOD_PROVISIONAL_DEFAULT = 0.10

#: Fallback used only when an element has too little real data to fit.
CV_FALLBACK = 0.20


def metal_basis(values: Dict[str, float]) -> Dict[str, float]:
    """Renormalise measured values over alloy elements only, to 100%."""
    alloy = {k: v for k, v in values.items() if k not in NON_ALLOY}
    total = sum(alloy.values())
    if total <= 0:
        return {}
    return {k: v * 100.0 / total for k, v in alloy.items()}


def derive() -> dict:
    spectra = load_spectra()
    grouped = group_by_component(spectra)

    # Surface-treatment labels describe a coating variant of a component, not a
    # component; their scatter is dominated by the treatment, so they are not
    # used to fit a component's intrinsic variance.
    groups = {
        name: ss
        for name, ss in grouped.items()
        if not is_surface_treatment(name) and len(ss) >= 3
    }

    # element -> list of (group_mean, group_stdev) on the metal basis
    observed: Dict[str, List[tuple]] = {}
    for name, ss in groups.items():
        bases = [metal_basis(s.values) for s in ss]
        elements = set().union(*[set(b) for b in bases]) if bases else set()
        for element in elements:
            xs = [b[element] for b in bases if element in b]
            if len(xs) < 3:
                continue
            mean = st.mean(xs)
            if mean <= 0:
                continue
            observed.setdefault(element, []).append((mean, st.stdev(xs)))

    # The additive floor is dominated by counting statistics and background
    # subtraction, which are largely instrument properties rather than
    # element-specific ones. So for an element with no low-concentration
    # observations, the defensible stand-in is the pooled floor from elements
    # that DO have low-concentration support - never that element's own
    # high-concentration scatter, which measures the proportional component
    # already carried by cv. (Using it as a floor gave Cu a 26.5 wt% floor,
    # a tolerance wider than the measurement itself.)
    pooled_low: List[float] = [
        sd
        for pairs in observed.values()
        for mean, sd in pairs
        if mean < LOW_CONC_WT
    ]
    pooled_floor = max(
        SIGMA_FLOOR_MIN, round(st.median(pooled_low), 4) if pooled_low else SIGMA_FLOOR_MIN
    )

    # Reference CV from well-supported elements, used only to decide which
    # elements are heterogeneity-dominated (not to overwrite any fitted value).
    well_supported_cvs = [
        st.median([sd / mean for mean, sd in pairs])
        for pairs in observed.values()
        if len([1 for mean, _ in pairs if mean > 0]) >= MIN_GROUPS
    ]
    reference_cv = st.median(well_supported_cvs) if well_supported_cvs else CV_FALLBACK

    elements_out: Dict[str, dict] = {}
    for element, pairs in sorted(observed.items()):
        n_groups = len(pairs)
        cvs = [sd / mean for mean, sd in pairs]
        low = [sd for mean, sd in pairs if mean < LOW_CONC_WT]

        cv = st.median(cvs)
        if low:
            floor = max(SIGMA_FLOOR_MIN, round(st.median(low), 4))
            floor_source = "fitted_low_conc"
        else:
            floor = pooled_floor
            floor_source = "pooled_across_elements"

        provisional = n_groups < MIN_GROUPS
        if provisional:
            cv = max(cv, CV_FALLBACK)

        # An element whose within-component CV is far above the well-supported
        # reference is not simply noisy - it is sampling more than one physical
        # regime. Cu and Zn span coating trace to matrix constituent, so their
        # ABSOLUTE level cannot gate identification, while a ratio built from
        # them (Sn/Cu for bronze) stays stable because the dilution cancels.
        heterogeneity_dominated = cv > 2.0 * reference_cv

        # The observed cv conflates two things: instrument imprecision, and
        # genuine composition differences between particles. For a
        # heterogeneity-dominated element the second term dominates, so using
        # the raw cv as a MEASUREMENT sigma is wrong - it yielded sigma_Cu =
        # 52 wt% at Cu = 88 wt%, a tolerance wider than the measurement.
        # `cv_scoring` is therefore capped at the well-supported reference for
        # use as measurement uncertainty, while `cv` is retained unmodified as
        # the honest observed spread.
        cv_cap = 2.0 * reference_cv
        cv_scoring = min(cv, cv_cap)

        elements_out[element] = {
            "sigma_floor_wt": round(floor, 4),
            "sigma_floor_source": floor_source,
            "cv": round(cv, 4),
            "cv_scoring": round(cv_scoring, 4),
            "cv_scoring_capped": cv_scoring < cv,
            "lod_wt": LOD_PROVISIONAL_DEFAULT,
            "lod_provisional": True,
            "n_groups": n_groups,
            "n_low_conc_groups": len(low),
            "conc_range_wt": [
                round(min(m for m, _ in pairs), 3),
                round(max(m for m, _ in pairs), 3),
            ],
            "provisional": provisional,
            "heterogeneity_dominated": heterogeneity_dominated,
            "prefer_ratio": heterogeneity_dominated,
        }

    return {
        "version": "1.0.0",
        "model": "sigma_e(x) = max(sigma_floor_wt, cv_scoring * x)   [wt%, metal basis]",
        "variance_component": "within-component across particles/sites/surface prep",
        "rationale": (
            "Conservative choice for assigning a NEW particle. Within-particle "
            "repeat noise is smaller and would overstate threshold sharpness "
            "(e.g. the F1a/F1b Mn boundary reads 4.7 sigma on within-particle "
            "noise but 1.7 sigma on within-component scatter)."
        ),
        "source": {
            "workbook": "data/EDS Consolidation.xlsx",
            "sheet": "Components",
            "n_spectra_total": len(spectra),
            "n_groups_used": len(groups),
            "group_criterion": (
                ">=3 real spectra, surface-treatment variant labels excluded"
            ),
        },
        "constants": {
            "sigma_floor_min_wt": SIGMA_FLOOR_MIN,
            "low_conc_threshold_wt": LOW_CONC_WT,
            "cv_fallback": CV_FALLBACK,
            "lod_provisional_default_wt": LOD_PROVISIONAL_DEFAULT,
        },
        "caveats": [
            "lod_wt is NOT fitted - it is a provisional placeholder and must be "
            "confirmed per element against the actual instrument and settings "
            "before an unreported element is treated as hard evidence of absence.",
            "Elements flagged provisional=true were fitted from fewer than "
            f"{MIN_GROUPS} component groups; treat their sigma as indicative only.",
            "cv is the raw observed within-component spread. cv_scoring is the "
            "value to use as MEASUREMENT uncertainty: for heterogeneity-dominated "
            "elements the raw cv also contains genuine particle-to-particle "
            "composition differences, and using it as sigma produced a tolerance "
            "wider than the measurement (sigma_Cu = 52 wt% at Cu = 88 wt%).",
            "Elements with prefer_ratio=true span trace-to-matrix roles (coating "
            "versus constituent). Their ABSOLUTE level must not gate identity; use "
            "a ratio (e.g. Sn/Cu for bronze), where the dilution cancels.",
            "C, O, N, F, Ca, K, Cl are excluded from the metal basis and "
            "therefore have no fitted sigma here.",
        ],
        "elements": elements_out,
    }


def main() -> None:
    model = derive()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")

    src = model["source"]
    print("wrote " + str(OUT_PATH))
    print(
        "fitted from "
        + str(src["n_groups_used"])
        + " component groups / "
        + str(src["n_spectra_total"])
        + " real spectra"
    )
    print("")
    header = (
        "element  floor_wt  floor_src      cv  cv_scor  n_grp   conc_range_wt  prov  ratio_only"
    )
    print(header)
    for element, d in model["elements"].items():
        rng = str(d["conc_range_wt"][0]) + "-" + str(d["conc_range_wt"][1])
        src = "fitted" if d["sigma_floor_source"] == "fitted_low_conc" else "pooled"
        print(
            "  "
            + element.ljust(5)
            + str(d["sigma_floor_wt"]).rjust(8)
            + src.rjust(11)
            + (str(round(d["cv"] * 100, 2)) + "%").rjust(8)
            + (str(round(d["cv_scoring"] * 100, 2)) + "%").rjust(9)
            + str(d["n_groups"]).rjust(7)
            + rng.rjust(16)
            + ("  YES" if d["provisional"] else "   no")
            + ("       YES" if d["prefer_ratio"] else "        no")
        )
    flagged = [e for e, d in model["elements"].items() if d["prefer_ratio"]]
    if flagged:
        print("")
        print(
            "heterogeneity-dominated (absolute level must NOT gate identity; "
            "use ratios): " + ", ".join(flagged)
        )


if __name__ == "__main__":
    main()
