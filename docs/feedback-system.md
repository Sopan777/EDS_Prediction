# DHATU BODH — Feedback & Continuous Improvement System

The Feedback System (`apps/feedback/`) bridges automated classification with human metallurgical expertise, creating an audited feedback loop for continuous model improvement.

---

## 1. Motivation

In high-reliability failure analysis:
- Surface oxidation, mechanical smear, or chemical plating can cause an EDS spectrum to deviate from nominal specification.
- An experienced metallurgical analyst examining physical wear markings or component geometry often possesses ground truth knowledge that complements the elemental spectrum.
- The feedback loop captures this expert input systematically without modifying the underlying deterministic rule engine without review.

---

## 2. Feedback Workflow

```
1. PREDICTION GENERATION
   - Engine predicts Material Family (e.g. F2 100Cr6) & Component (e.g. Armature Bolt)
   - Results displayed in priority order with confidence & distance breakdown
          |
          v
2. ANALYST EVALUATION
   - Analyst inspects physical sample or SEM micrograph
          |
          +-----------------------------------+
          |                                   |
          v                                   v
   [ Confirm Match ]                 [ Suggest Correction ]
   - Clicks "Confirm Identification"  - Selects corrected family/component
   - Writes verification to DB       - Enters domain notes / reason
          |                                   |
          +-----------------+-----------------+
                            |
                            v
3. PERSISTENCE (`PredictionFeedback` table)
   - Analysis ID, measured spectrum, predicted vs confirmed labels, analyst name
          |
          v
4. AUDIT & RETRAINING LOOP
   - History tab displays all analyst feedback
   - Exportable via GET /api/feedback for retraining empirical fingerprints
```

---

## 3. Retraining Empirical Fingerprints

Feedback records can be exported and combined with the primary dataset (`EDS Consolidation_xlsx(1).xlsx`) to update component fingerprints:

```bash
python training/build_component_fingerprints.py
```

This ensures that component fingerprints become progressively more accurate over time as new verified spectra are collected.
