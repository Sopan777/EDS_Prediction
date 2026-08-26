"""
training/derive_knowledge.py
============================
Build the material knowledge base from the REAL measured spectra.

Separation of concerns (this is the important part)
--------------------------------------------------
* Family PREDICATES are metallurgical, not learned. "Austenitic 18/8 stainless
  means Cr>12 with Ni>5 and Cr/Ni~2" is standing domain knowledge that holds
  independently of these 173 spectra. Encoding it as a predicate is what makes
  a family with one member (F3 tool steel, F5 Ni-base) usable at all: the
  system is testing a specification, not fitting a distribution.

* Element BANDS are derived from the real spectra, widened by the fitted sigma
  model. Nothing here is invented; where support is thin the entry is flagged
  ``provisional`` and the caveat travels with the prediction.

This inverts the failed approach in ``training/train_rules.py``, which derived
*thresholds* greedily from synthetic jitter and then pruned away any condition
that did not improve precision on that same synthetic split - deleting the Mn
lower bound from 30 of 36 rules, because no synthetic sample ever tested it.

Output: ``rule_engine/knowledge/materials.json``

Stdlib only.
"""

from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rule_engine.normalize import (  # noqa: E402
    get_sigma_model,
    normalize_spectrum,
)
from rule_engine.real_data import (  # noqa: E402
    group_by_component,
    is_surface_treatment,
    load_spectra,
)

OUT_PATH = (
    Path(__file__).resolve().parent.parent
    / "rule_engine"
    / "knowledge"
    / "materials.json"
)

#: Minimum real spectra behind a band before it is treated as well supported.
MIN_SPECTRA_FOR_BAND = 3

#: Minimum distinct components behind a family before its bands are trusted.
MIN_COMPONENTS_FOR_FAMILY = 2

#: How many sigma to widen an observed [min, max] band by. 2 sigma keeps a
#: genuine member inside its own band while leaving the family boundaries
#: distinguishable; hard rejection uses a wider margin still (see scoring).
BAND_WIDEN_SIGMA = 2.0


# ---------------------------------------------------------------------------
# Family definitions - metallurgical predicates over the metal basis
# ---------------------------------------------------------------------------
# Each entry: (id, label, grade_hint, predicate, discriminators, note)
# The predicate receives a dict of metal-basis wt% and returns True/False.
# Order is irrelevant: every matching family is returned, so an ambiguous
# composition yields a SET rather than whichever rule happened to fire first.

def _g(m: Dict[str, float], e: str) -> float:
    return m.get(e, 0.0)


FAMILY_DEFS: List[dict] = [
    {
        "id": "F7",
        "label": "Au-plated electrical contact",
        "grade_hint": "Au plating on Cu/Ni substrate",
        "predicate": lambda m: _g(m, "Au") > 50.0,
        "discriminators": ["Au"],
        "note": "Plating dominates the analysed volume; substrate may be visible beneath.",
    },
    {
        "id": "F6a",
        "label": "Cu-Sn bronze / Cu-Sn metal matrix composite",
        "grade_hint": "CuSn8 and similar",
        "predicate": lambda m: _g(m, "Cu") > 40.0 and _g(m, "Au") <= 50.0,
        "discriminators": ["Cu", "Sn", "Sn/Cu"],
        "note": (
            "Sn/Cu is the stable fingerprint; absolute Cu is unreliable because "
            "the seal-ring matrix is PTFE-loaded and dilutes every metal reading."
        ),
    },
    {
        "id": "F6b",
        "label": "Cu-Sn bronze layer on steel (bimetallic seal ring)",
        "grade_hint": "CuSn overlay on steel backing",
        "predicate": lambda m: 8.0 <= _g(m, "Cu") <= 40.0
        and 20.0 <= _g(m, "Fe") <= 85.0
        and _g(m, "Sn") > 0.5,
        "discriminators": ["Cu", "Sn", "Sn/Cu"],
        "note": (
            "The interaction volume spans a bronze overlay and its steel backing, "
            "so BOTH Cu and Fe are matrix-level. Real HP-sealing references sit at "
            "Fe 58-64 / Cu 32-36 on the metal basis - between the Cu-rich and "
            "steel families, which is why a single-material predicate set missed "
            "them entirely. Report as a layered/bimetallic result, not one alloy."
        ),
    },
    {
        "id": "F5",
        "label": "Ni-base alloy",
        "grade_hint": "Ni-Cr alloy",
        "predicate": lambda m: _g(m, "Ni") > 50.0,
        "discriminators": ["Ni", "Cr"],
        "note": "Ni is the matrix, not an addition.",
    },
    {
        "id": "F4",
        "label": "Austenitic stainless steel 18/8",
        "grade_hint": "X8CrNiS18-9 / X12CrNiS19-8",
        "predicate": lambda m: _g(m, "Cr") > 12.0 and _g(m, "Ni") > 5.0,
        "discriminators": ["Cr", "Ni", "Cr/Ni"],
        "note": (
            "Requires BOTH Cr and Ni at alloy level. If either was not analysed "
            "this family is unevaluable, never a match - the failure that "
            "produced 'Magnet housing' for a plain 1.5Mn steel."
        ),
    },
    {
        "id": "F3",
        "label": "Tool / high-speed steel",
        "grade_hint": "HSS M2 / Sl2b17 (S6-5-2)",
        "predicate": lambda m: (_g(m, "W") > 3.0 or _g(m, "Mo") > 3.0)
        and _g(m, "Fe") > 50.0,
        "discriminators": ["W", "Mo", "V", "Cr"],
        "note": "W-Mo-V carbide formers are decisive and near-unique in this domain.",
    },
    {
        "id": "F8a",
        "label": "Zn-coated steel (galvanic / electroplated)",
        "grade_hint": "Zn plating on steel",
        "predicate": lambda m: _g(m, "Zn") > 5.0 and _g(m, "P") <= 5.0,
        "discriminators": ["Zn"],
        "note": (
            "A measured coating LAYER, distinct from a coating trace. Fe is "
            "deliberately unconstrained: it reads ~72 wt% through a thin layer "
            "but under 2 wt% through a thick one, where the substrate is simply "
            "not in the interaction volume. Requiring Fe>40 lost every "
            "thick-coating spectrum. Substrate grade is NOT determinable here."
        ),
    },
    {
        "id": "F8b",
        "label": "Zn-phosphate conversion coating on steel",
        "grade_hint": "Zn phosphating",
        "predicate": lambda m: _g(m, "P") > 5.0 and _g(m, "Zn") > 3.0,
        "discriminators": ["P", "Zn"],
        "note": (
            "Zn + P together at layer level, with high oxygen in the as-measured "
            "spectrum (phosphate anion). Distinguished from F8a by P, and from "
            "plain steel by both. Substrate grade is NOT determinable."
        ),
    },
    {
        "id": "F2",
        "label": "Low-alloy Cr bearing steel",
        "grade_hint": "100Cr6 / Sl2 B1",
        "predicate": lambda m: 1.2 <= _g(m, "Cr") <= 12.0
        and _g(m, "Ni") <= 5.0
        and _g(m, "Fe") > 80.0
        and _g(m, "W") <= 3.0
        and _g(m, "Mo") <= 3.0,
        "discriminators": ["Cr", "Mn", "Si"],
        "note": "Cr ~1.3-1.9 with low Mn. Carbon content is not determinable by EDS.",
    },
    {
        "id": "F1c",
        "label": "Si-Cr spring steel",
        "grade_hint": "VDSiCr / DIN 17223",
        "predicate": lambda m: _g(m, "Si") >= 1.2
        and _g(m, "Cr") < 1.2
        and _g(m, "Fe") > 90.0,
        "discriminators": ["Si", "Cr", "Mn"],
        "note": "Elevated Si with only residual Cr.",
    },
    {
        "id": "F1b",
        "label": "~1.5 Mn plain carbon steel",
        "grade_hint": "16MnCr5-family / 1.5Mn steel",
        "predicate": lambda m: _g(m, "Mn") >= 1.2
        and _g(m, "Cr") < 1.2
        and _g(m, "Si") < 1.2
        and _g(m, "Fe") > 90.0,
        "discriminators": ["Mn"],
        "note": (
            "Separated from F1a only by Mn. The boundary is ~1.7 sigma on "
            "within-component scatter, so it needs an ambiguity band, not a cut."
        ),
    },
    {
        "id": "F1a",
        "label": "Plain / low-Mn carbon steel",
        "grade_hint": "plain C steel, C45PbK, En1A and similar",
        "predicate": lambda m: _g(m, "Mn") < 1.2
        and _g(m, "Cr") < 1.2
        and _g(m, "Si") < 1.2
        and _g(m, "Fe") > 90.0,
        "discriminators": ["Mn"],
        "note": (
            "The largest and least specific family. Many components share it, "
            "so component identity is not recoverable here by composition alone."
        ),
    },
]

#: Ratio constraints per family. Ratios survive closure/dilution error, so they
#: gate families whose absolute levels are unreliable.
_SN_CU_BRONZE = {
    "ratio": "Sn/Cu",
    "min": 0.04,
    "max": 0.16,
    "rationale": (
        "CuSn bronze. Observed 0.106-0.109 on the real bronze particle and "
        "0.10-0.12 on the two seal-ring references. Normalisation-invariant, so "
        "it survives the PTFE dilution that makes absolute Cu unreliable."
    ),
}

FAMILY_RATIOS: Dict[str, List[dict]] = {
    "F4": [
        {
            "ratio": "Cr/Ni",
            "min": 1.4,
            "max": 3.2,
            "rationale": "18/8 austenitic stoichiometry; observed 1.6-2.2 in real spectra.",
        }
    ],
    # Both bronze families carry the same Sn/Cu fingerprint - the overlay-on-steel
    # case dilutes Cu and Sn together, so their ratio is unchanged.
    "F6a": [_SN_CU_BRONZE],
    "F6b": [_SN_CU_BRONZE],
}


def assign_families(metal: Dict[str, float]) -> List[str]:
    """Every family whose metallurgical predicate the composition satisfies."""
    return [f["id"] for f in FAMILY_DEFS if f["predicate"](metal)]


def _band(
    values: List[float], element: str, sigma_model
) -> Tuple[float, float, float]:
    """Return ``(lo, hi, sigma_at_mean)`` widened by BAND_WIDEN_SIGMA."""
    lo, hi = min(values), max(values)
    mean = st.mean(values)
    sigma = sigma_model.sigma(element, mean)
    return (
        max(0.0, round(lo - BAND_WIDEN_SIGMA * sigma, 3)),
        round(hi + BAND_WIDEN_SIGMA * sigma, 3),
        round(sigma, 4),
    )


def derive() -> dict:
    sigma_model = get_sigma_model()
    spectra = load_spectra()

    # Normalise every real spectrum onto the metal basis.
    records: List[dict] = []
    for s in spectra:
        ns = normalize_spectrum(s.values, analysed_elements=list(s.values))
        metal = {e: ns.metal(e) for e in ns.alloy_elements()}
        if not metal:
            continue
        records.append(
            {
                "component": s.component,
                "surface_variant": is_surface_treatment(s.component),
                "metal": metal,
                "families": assign_families(metal),
            }
        )

    # -- per-family element bands ----------------------------------------
    families_out: Dict[str, dict] = {}
    for fam in FAMILY_DEFS:
        fid = fam["id"]
        members = [r for r in records if fid in r["families"]]
        components = sorted({r["component"] for r in members})
        real_components = sorted(
            {r["component"] for r in members if not r["surface_variant"]}
        )

        by_element: Dict[str, List[float]] = {}
        for r in members:
            for element, value in r["metal"].items():
                by_element.setdefault(element, []).append(value)

        n_members = len(members)
        elements_out: Dict[str, dict] = {}
        for element, values in sorted(by_element.items()):
            lo, hi, sigma = _band(values, element, sigma_model)
            present_in = len(values)
            elements_out[element] = {
                "band_wt": [lo, hi],
                "observed_wt": [round(min(values), 3), round(max(values), 3)],
                "mean_wt": round(st.mean(values), 3),
                "sigma_at_mean": sigma,
                "n_spectra": present_in,
                # "required" means: every member spectrum that was analysed for
                # this element actually showed it. A grade requiring an element
                # is CONTRADICTED when that element is analysed and absent.
                "required": present_in == n_members and st.mean(values) > 0.3,
                "provisional": present_in < MIN_SPECTRA_FOR_BAND,
                "prefer_ratio": sigma_model.prefer_ratio(element),
            }

        families_out[fid] = {
            "label": fam["label"],
            "grade_hint": fam["grade_hint"],
            "discriminators": fam["discriminators"],
            "note": fam["note"],
            "ratios": FAMILY_RATIOS.get(fid, []),
            "n_spectra": n_members,
            "n_components": len(real_components),
            "components": real_components,
            "surface_variants": sorted(
                {r["component"] for r in members if r["surface_variant"]}
            ),
            "elements": elements_out,
            "provisional": len(real_components) < MIN_COMPONENTS_FOR_FAMILY,
        }

    # -- component -> family map (many-to-many by construction) ----------
    grouped = group_by_component(spectra)
    components_out: Dict[str, dict] = {}
    for name, ss in sorted(grouped.items()):
        member_records = [r for r in records if r["component"] == name]
        fam_counts: Dict[str, int] = {}
        for r in member_records:
            for fid in r["families"]:
                fam_counts[fid] = fam_counts.get(fid, 0) + 1
        components_out[name] = {
            "n_spectra": len(ss),
            "families": sorted(fam_counts, key=lambda k: -fam_counts[k]),
            "family_spectrum_counts": fam_counts,
            "surface_treatment_variant": is_surface_treatment(name),
            "ambiguous": len(fam_counts) > 1,
        }

    unassigned = [r["component"] for r in records if not r["families"]]

    return {
        "version": "1.0.0",
        "target": "material family -> grade hint -> ranked candidate components",
        "design": {
            "family_predicates": (
                "Metallurgical and standing domain knowledge, NOT fitted. This is "
                "what makes single-member families usable: the system tests a "
                "specification rather than fitting a distribution."
            ),
            "element_bands": (
                "Derived from real measured spectra on the metal basis, widened by "
                + str(BAND_WIDEN_SIGMA)
                + " sigma from the fitted sigma model."
            ),
            "why_not_component_level": (
                "On real component centroids with heteroscedastic sigma, 20 of 630 "
                "component pairs are indistinguishable at 3 sigma and ALL of them "
                "are within a single family - zero cross-family collisions. "
                "Component identity is therefore not recoverable from EDS "
                "composition alone; family is."
            ),
        },
        "source": {
            "workbook": "data/EDS Consolidation.xlsx",
            "sheet": "Components",
            "n_spectra": len(spectra),
            "n_spectra_normalised": len(records),
            "sigma_model_version": sigma_model.version,
        },
        "caveats": [
            "Carbon content is NOT determinable by EDS (light element, carbon tape, "
            "coating), so grades are separated by alloying elements only. A family "
            "label such as 'plain carbon steel' must never be reported as a "
            "specific carbon grade.",
            "Bands describe the real spectra available, not the full alloy "
            "specification. Where a DIN/EN grade range is known it should replace "
            "the derived band; entries flagged provisional rest on <"
            + str(MIN_SPECTRA_FOR_BAND)
            + " spectra.",
            "Families flagged provisional have fewer than "
            + str(MIN_COMPONENTS_FOR_FAMILY)
            + " distinct components and their bands should be treated as indicative.",
            "Elements flagged prefer_ratio span trace-to-matrix roles; their "
            "absolute level must not gate identity.",
        ],
        "families": families_out,
        "components": components_out,
        "unassigned_spectra_components": sorted(set(unassigned)),
    }


def main() -> None:
    kb = derive()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(kb, indent=2) + "\n", encoding="utf-8")

    print("wrote " + str(OUT_PATH))
    src = kb["source"]
    print(
        "from "
        + str(src["n_spectra_normalised"])
        + "/"
        + str(src["n_spectra"])
        + " real spectra"
    )
    print("")
    print("family  n_spec  n_comp  prov  label")
    for fid, f in kb["families"].items():
        print(
            "  "
            + fid.ljust(6)
            + str(f["n_spectra"]).rjust(6)
            + str(f["n_components"]).rjust(8)
            + ("   YES" if f["provisional"] else "    no")
            + "  "
            + f["label"]
        )
    amb = [c for c, d in kb["components"].items() if d["ambiguous"]]
    print("")
    print("components whose spectra span >1 family: " + str(len(amb)))
    for c in amb:
        d = kb["components"][c]
        print("   " + c.ljust(28) + str(d["family_spectrum_counts"]))
    if kb["unassigned_spectra_components"]:
        print("")
        print("components with spectra matching NO family (need review):")
        for c in kb["unassigned_spectra_components"]:
            print("   " + c)


if __name__ == "__main__":
    main()
