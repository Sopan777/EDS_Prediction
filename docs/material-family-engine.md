# DHATU BODH — Material Family Engine

The Material Family Engine (`rule_engine/`) is a deterministic expert system designed to classify EDS spectra into standardized alloy families with full transparency and zero non-deterministic hallucinations.

---

## 1. Material Family Taxonomy

| Code | Human-Readable Material Family Name | Primary Grade Hint | Characteristic Elements |
|---|---|---|---|
| **F1a** | Plain / Low-Manganese Carbon Steel | C15 / C45 / Mild Steel | Fe Bal., Mn < 0.8%, Si < 0.4% |
| **F1b** | ~1.5% Manganese Carbon Steel | 16MnCr5 / Case-Hardening | Fe Bal., Mn 1.0 – 1.6%, Cr 0.8 – 1.2% |
| **F1c** | Silicon-Chromium Spring Steel | 54SiCr6 / VDSiCr / DIN 17223 | Fe Bal., Si 1.2 – 1.6%, Cr 0.5 – 0.9% |
| **F2** | Low-Alloy Chromium Bearing Steel | 100Cr6 / Sl2 B1 / SAE 52100 | Fe Bal., Cr 1.3 – 1.65%, Mn ~0.35% |
| **F3** | High-Speed Tool Steel | M2 / S6-5-2 / 1.3343 | W 5.5 – 6.7%, Mo 4.5 – 5.5%, V 1.7 – 2.1%, Cr ~4% |
| **F4** | Austenitic Stainless Steel 18/8 | AISI 304 / X8CrNiS18-9 | Cr 17.5 – 19.5%, Ni 8.0 – 10.5%, Fe Bal. |
| **F5** | Nickel-Base Superalloy | Inconel / Ni-Cr | Ni > 50%, Cr 15 – 25%, Fe < 10% |
| **F6a** | Copper-Tin Bronze | CuSn8 / Phosphor Bronze | Cu 90 – 93%, Sn 7 – 9%, P 0.05 – 0.4% |
| **F6b** | Bimetallic Cu-Sn Bronze on Steel | Bushing Liner on Steel | Cu 40 – 70%, Sn 3 – 8%, Fe 25 – 55% |
| **F7** | Gold-Plated Electrical Contact | Au Plating on Ni/Cu Underlayer | Au > 15%, Ni 10 – 40%, Cu 20 – 60% |
| **F8a** | Zinc-Coated / Galvanized Steel | Electroplated / Hot-Dip Zn | Zn > 15%, Fe Bal. |
| **F8b** | Zinc-Phosphate Conversion Coating | Bonded Anti-Wear / Primer | Zn 5 – 25%, P 2 – 10%, Fe Bal. |

---

## 2. Invariant Principles

The engine adheres to 5 fundamental physical invariants tested in `tests/test_scoring_invariance.py`:

1. **Carbon/Contamination Invariance**: Adding arbitrary percentages of non-metallic contaminants (C, O, N) does NOT change the predicted alloy family.
2. **Scale Invariance**: Proportional scaling of input concentrations (e.g. 50 wt% vs 100 wt%) yields identical relative alloy scores.
3. **Order Invariance**: The dictionary key ordering of elements (e.g. `{'Cr': 18, 'Ni': 8}` vs `{'Ni': 8, 'Cr': 18}`) has zero effect on calculations.
4. **Honest Compatibility Capping**: No prediction ever returns $1.000$ ($100.0\%$) compatibility because EDS is inherently semi-quantitative. Scores are bounded at $\le 0.98$.
5. **Safe Abstention**: If an unknown material (e.g. Pure Titanium, Polymer, or corrupted detector noise) is scanned, the engine outputs `UNKNOWN` or `INSUFFICIENT_DATA` rather than forcing an inaccurate match.

---

## 3. Stoichiometric Ratio Gates

When elemental concentration bands overlap between two related families, the engine enforces deterministic stoichiometric ratio gates:

- **Cr / Ni Gate (F4 Austenitic Stainless)**:
  $$1.80 \le \frac{\text{Cr}}{\text{Ni}} \le 2.80$$
  *Metallurgical Rationale*: Prevents misclassifying duplex stainless steels ($Cr/Ni > 3.0$) or high-nickel superalloys ($Cr/Ni < 1.0$) as standard 18/8 austenitic stainless.

- **Cu / Sn Gate (F6a Bronze)**:
  $$6.0 \le \frac{\text{Cu}}{\text{Sn}} \le 16.0$$
  *Metallurgical Rationale*: Guarantees authentic bronze matrix stoichiometry. High-lead brasses or solder debris are rejected.

- **W / Mo Gate (F3 High-Speed Tool Steel)**:
  $$0.80 \le \frac{\text{W}}{\text{Mo}} \le 1.60$$
  *Metallurgical Rationale*: Uniquely identifies standard tungsten-molybdenum M2 tool steel carbide balances.
