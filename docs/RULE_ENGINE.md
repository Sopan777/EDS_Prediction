# Material-Family Scoring Engine — Architecture

This document describes the **current** prediction engine
(`rule_engine/scoring.py`), which replaced the conjunctive rule engine
originally documented here. The old engine (`rule_engine/engine.py` +
`rule_engine/rules/rules.json`) is retired as a decision authority; see
[EDS_AUDIT.md](EDS_AUDIT.md) for the full history and why. It is kept in the
repo only so the quarantined legacy test suite has something to exercise
(`pytest --run-legacy`).

## Overview

The engine takes a spectrum's elemental composition (weight %) and identifies
a **material family** — never a single component name — with an explicit
grade hint, a ranked list of candidate components, and abstention as a
first-class answer.

**Key properties:**

- Pure Python stdlib implementation (no pandas, numpy, or scikit-learn)
- Deterministic and fully explainable — every check that ran is retained
- Scored, not filtered: compatibility is computed per input, never a stored
  constant
- Absence is never treated as evidence for or against anything by default —
  see "Three-state missingness" below
- 6/6 correct on the real analyst-labelled particles; 99.3% family accuracy
  under leave-one-component-out (see [EDS_AUDIT.md](EDS_AUDIT.md) §15)

## Architecture

```
data/EDS Consolidation.xlsx (Components sheet, 173 real spectra)
        |
        v
training/derive_sigma_model.py --> rule_engine/knowledge/sigma_model.json
        |                          (per-element measurement uncertainty,
        |                           fitted from real repeat spectra)
        v
training/derive_knowledge.py  --> rule_engine/knowledge/materials.json
        |                          (family predicates: metallurgical, not
        |                           fitted + element bands: derived from
        |                           real spectra, widened by sigma)
        v
rule_engine/
  real_data.py       - loads the 173 real spectra (stdlib zipfile + ElementTree)
  normalize.py        - canonicalise element names, 3-state missingness,
                        metal-basis renormalisation, sigma lookup
  scoring.py           - score_family(), predict_spectrum(), predict_particle()
  validator.py         - validate_knowledge_base(); called at KnowledgeBase.load()
```

`eds_pipeline.py` and `app_rule.py` are the two entry points; both call
`rule_engine.scoring` directly.

## Why family, not component

Component identity turns out not to be recoverable from EDS composition
alone. Measured on real component centroids with concentration-dependent
measurement uncertainty (`sigma(x) = max(floor, cv * x)`, fitted from repeat
spectra): of 630 component pairs, colliding pairs at every noise level tested
stay **entirely within a single material family** — zero cross-family
collisions. The source reports agree: they assign a chemistry class plus a
*list* of probable source components, sometimes explicitly marked uncertain
("Magnet Nut, NR nut??"), never one component name.

## Three-state missingness

Every element in every spectrum is one of:

| State | Meaning | Effect on a family requiring this element |
|---|---|---|
| `MEASURED` | a real quantity, with a real uncertainty | checked against the band |
| `BELOW_LOD` | analysed, not detected | **contradicts** the family — positive evidence of absence |
| `NOT_ANALYSED` | never in the analysed column set | family is **unevaluable** on this element — never passes, never confirms |

Collapsing these into a single `0.0` — as the retired engine did — meant a
"forbidden element" check written as `<= 0.0` passed **vacuously** for any
unreported element, and a family requiring an element that was simply never
measured could still match. That is the direct mechanism behind
`{"S": 0.2}` → "Guide Bush" at confidence 1.00 in the old engine, for a
material whose every reference spectrum carried 1.12–1.60 wt% Mn.

## Metal-basis normalisation

EDS reports here use "All elements analysed (Normalised)", forcing every
spectrum to sum to 100%. C, O, N, F come largely from carbon tape, surface
oxide and mounting medium rather than the material, so absolute weight % are
not comparable between spectra — within one real particle, C alone ranges
3.81 to 15.82 wt%, dragging every other element with it.

`rule_engine/normalize.py` renormalises over alloy elements only (excluding
C, O, N, F, Ca, K, Na, Cl, Mg) before any comparison happens. On seven repeat
spectra of one real particle, this collapsed Fe's coefficient of variation
from 5.96% to 0.67%.

A separate **coating channel** captures elements that are usually a surface
treatment rather than an alloying addition (Zn, P, Au, Cd) *when* their
share of the alloy-candidate basis is below a threshold (3.0%, versioned in
`normalize.py` as `COATING_TRACE_MAX_BASIS_PCT`) — distinguishing a 0.84 wt%
Zn coating trace from a measured Zn coating layer at tens of percent.

## Scoring (`rule_engine/scoring.py: score_family`)

For each family and each spectrum:

1. **Required elements** must be `MEASURED` and in-band, or the family is
   `CONTRADICTED` (if `BELOW_LOD`) or `UNEVALUABLE` (if `NOT_ANALYSED`).
2. **Band checks** on every element the family describes. Only a *decisive*
   element (required, or listed as a discriminator) whose band rests on
   sufficient data may **veto** the family when out of band; an incidental
   element out of band instead costs compatibility as `unexplained`, capped
   so it cannot outweigh strong evidence elsewhere. This asymmetry matters:
   without it, a one-spectrum incidental Cr band once rejected a real bronze
   particle outright despite Cu, Sn and the Sn/Cu ratio all matching; and
   without the opposite guard, an in-band but non-decisive Fe reading could
   wrongly confirm a family whose actual defining elements were never
   measured.
3. **Foreign-element rejection**: an alloy element the family does not
   describe at all, present above 2.0 wt%, contradicts the family.
4. **Ratio gates** — e.g. `Sn/Cu` for CuSn bronze, `Cr/Ni` for austenitic
   stainless. Ratios survive the closure/dilution error that makes absolute
   weight % unreliable, and are the strongest evidence term when they pass.
5. **Verdict**: `CONTRADICTED` if anything blocked; `UNEVALUABLE` if a
   required/discriminating element was never analysed and nothing else
   *confirms* the family (cost-only penalties from non-decisive elements do
   not count as confirmation); otherwise `FEASIBLE`.
6. **Compatibility** (only for `FEASIBLE`):
   `exp(-0.5 * distance²) * evidence * quality`, capped at 0.95. It is a
   goodness-of-fit statistic, never a probability — with six real labelled
   particles no honest calibration is possible.

## Decision (`predict_spectrum` / `predict_particle`)

Four gates, checked in order, any of which produces `UNKNOWN`:

1. **Insufficient metal signal** — alloy elements are below 8% of the
   as-measured spectrum (below the ~24% seen in the real PTFE-diluted bronze
   particle, so this only fires on genuinely non-metallic input).
2. **No feasible family**, or the best feasible family's compatibility is
   below 0.15 (clearing the hard constraints is necessary but not sufficient
   — a family can be non-contradicted and still fit badly).
3. **Insufficient evidence** — fewer than half of the leading family's
   discriminators were actually measured.
4. **Insufficient margin** — the top two families' compatibility differ by
   less than 0.15. This produces `AMBIGUOUS`, not `UNKNOWN`: the tied
   families are returned as a set, matching how the source reports
   themselves record uncertainty.

Input carrying a data-quality problem (a negative weight %, a total above
100, a duplicated element key) may still be identified, but its compatibility
is capped at 0.45 and a caveat is attached — such input must never present as
a clean high-confidence result.

`predict_particle` pools evidence across a table's spectra rather than
voting on them: a family contradicted by *any* spectrum is disqualified
outright, and compatibility for a family confirmed by more spectra is
rewarded over one confirmed by only a few. This replaces the retired
majority-vote roll-up, which hardcoded its low-confidence flag to `None` and
averaged probability only over the spectra where the winner already led.

## Knowledge base format (`rule_engine/knowledge/materials.json`)

```json
{
  "version": "1.0.0",
  "families": {
    "F6a": {
      "label": "Cu-Sn bronze / Cu-Sn metal matrix composite",
      "grade_hint": "CuSn8 and similar",
      "discriminators": ["Cu", "Sn", "Sn/Cu"],
      "ratios": [
        {"ratio": "Sn/Cu", "min": 0.04, "max": 0.16, "rationale": "..."}
      ],
      "elements": {
        "Cu": {"band_wt": [29.7, 134.5], "required": true, "prefer_ratio": false, "n_spectra": 3},
        "Sn": {"band_wt": [3.0, 9.5],   "required": true, "prefer_ratio": false, "n_spectra": 3}
      },
      "components": ["Blade Terminal", "CRI Sealing ring"],
      "provisional": false
    }
  }
}
```

- `discriminators` — every non-ratio entry must be a key in that same
  family's `elements`; every ratio entry (`"Sn/Cu"`) must have a matching
  entry in that family's `ratios`. Enforced by `validate_knowledge_base` at
  load time (see below).
- `elements[e].required` — `true` only if every spectrum behind this family
  showed the element at a materially significant level.
- `elements[e].prefer_ratio` — `true` for elements whose absolute level spans
  a trace-to-matrix role (from the fitted sigma model); such elements are
  checked loosely and carry their real weight through a ratio instead.
- `provisional` — fewer than 2 distinct real components back this family
  (e.g. F3 tool steel, F5 Ni-base, F6b bronze-on-steel each have exactly one);
  bands should be treated as indicative, not firm.

This file is **generated** by `training/derive_knowledge.py` — never
hand-edit it. Family *predicates* (the metallurgical logic deciding which
family a spectrum belongs to, e.g. "Cr > 12 and Ni > 5 ⇒ austenitic 18/8")
live in `training/derive_knowledge.py` itself, not in the JSON: they are
standing domain knowledge, not fitted, which is what makes a single-member
family usable at all.

## Validation at load time

`KnowledgeBase.load()` calls `rule_engine.validator.validate_knowledge_base`
before returning, and raises `ValueError` if the file is structurally broken
— an inverted band (`lo > hi`), a discriminator naming an element or ratio
absent from that same family's own data, or an empty `families` dict. This
closes a gap the audit found in the *retired* engine too: nothing ever called
`validator.py`'s checks against `rules.json` at runtime, so a broken rule
file would have failed silently, deep inside scoring, rather than loudly at
load time.

## Regenerating the knowledge base

```bash
python training/derive_sigma_model.py   # fits sigma_model.json from real repeat spectra
python training/derive_knowledge.py     # builds materials.json (predicates + bands)
python training/validate_loco.py        # leave-one-component-out: honest generalisation check
```

Run all three after changing `rule_engine/real_data.py`'s source data, adding
a family predicate, or adjusting a tuning constant in `normalize.py` or
`derive_sigma_model.py`.

## Regenerating the retired rules.json (legacy only)

```bash
python training/train_rules.py       # only relevant to the retired engine.py path
python training/evaluate_rules.py
python training/analyze_dataset.py
```

These operate on `data/synthetic_eds_data.csv` — the old reference table plus
multiplicative jitter, with no independent measurement information — and
feed the retired conjunctive engine. Kept for the quarantined legacy test
suite only; do not build new functionality on this path.

## Comparison with the retired engine

| Aspect | Retired (`engine.py`) | Current (`scoring.py`) |
|---|---|---|
| Matching | conjunctive AND filter | hard feasibility + soft distance + ratios |
| Confidence | constant, frozen at training time | computed per input, capped at 0.95 |
| Missing element | coerced to `0.0` | three states: measured / below-LOD / not-analysed |
| Target | one of 36 component names | family → grade hint → ranked candidates |
| Abstention | only on zero matching rules | four explicit gates; ambiguous sets supported |
| Reference data | synthetic CSV (jittered lookup table) | 173 real spectra |
| Validated by | self-selecting test fixture | leave-one-component-out (99.3% family accuracy) |
| Real-particle accuracy | 0/5 | 6/6 |
