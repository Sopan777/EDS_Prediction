# DHATU BODH — Prediction Pipeline Walkthrough

This document traces the complete end-to-end execution path when an EDS spectrum or multi-spectrum report is submitted for analysis.

---

## 1. Flowchart of Prediction Lifecycle

```
[ EDS Input ] (PDF / CSV / JSON / Manual wt%)
      |
      v
1. INGESTION & EXTRACTION (services/eds/extractor.py)
   - PDF geometry table parsing (PyMuPDF)
   - Clean numeric composition extraction
   - Detection of analysed vs unanalysed elements
      |
      v
2. PARTICLE POOLING (if multiple spectra provided)
   - Corroborates readings across particle sites
   - Calculates arithmetic centroid composition
      |
      v
3. METAL-BASIS NORMALIZATION (rule_engine/normalize.py)
   - Excludes non-alloy elements (C, O, N, F, Ca, K, Na, Cl, Mg)
   - Renormalizes alloy elements to 100% basis
      |
      v
4. MATERIAL FAMILY MATCHING (rule_engine/scoring.py)
   - Evaluates nominal concentration bands per family
   - Enforces stoichiometric ratio gates (Cr/Ni, Cu/Sn, W/Mo)
   - Computes deterministic compatibility score (0-100%)
   - Classifies status: IDENTIFIED | AMBIGUOUS | UNKNOWN
      |
      v
5. COMPONENT-LEVEL MATCHING (rule_engine/component_scoring.py)
   - Scopes candidate pool to top predicted family
   - Computes standardized distance z = |x - median| / IQR
   - Penalizes foreign/unexpected elements (2.50x weight)
   - Checks evidence sufficiency (fraction of expected elements present)
   - Ranks top 10 empirical components
      |
      v
6. METALLURGICAL CONFLICT DETECTION (rule_engine/conflict_detector.py)
   - Compares declared material metadata (e.g. '100Cr6') with measured EDS family
   - Flags critical discrepancies, plating effects, or surface contaminants
      |
      v
7. PERSISTENCE & RESULTS DELIVERY (services/prediction/engine.py)
   - Writes record to AnalysisHistory table
   - Delivers structured JSON response to UI
```

---

## 2. Step-by-Step Breakdown

### Step 1: Ingestion & Extraction
- **PDF Extraction**: AZtec and Phenom instruments output vector tables. PyMuPDF extracts cell text coordinates to ensure decimal accuracy (avoiding OCR misinterpretations like `1.05%` $\to$ `105%`).
- **State Handling**: Missing elements are distinguished as `NOT_ANALYSED` vs `BELOW_LOD` (Limit of Detection). An element that was not scanned cannot be assumed to be 0 wt%.

### Step 2: Particle Pooling
When an analyst scans multiple spots on the same debris particle:
- Each individual spectrum is scored independently.
- If one spectrum exhibits an impossible chemistry (e.g. 50% Cu on a steel bolt), the system flags local contamination.
- The pooled average represents the particle's nominal bulk metallurgy.

### Step 3: Metal-Basis Renormalization
ASTM E1508 notes that light elements ($Z < 11$, specifically Carbon and Oxygen) have low fluorescence yield, heavy matrix absorption, and frequent atmospheric/hydrocarbon contamination in SEM vacuum chambers.
- DHATU BODH strips `C, O, N, F, Ca, K, Na, Cl, Mg` from the alloy calculation.
- The remaining metallic elements ($Fe, Cr, Ni, Mn, Si, Mo, Cu, Sn, Zn, W, V$, etc.) are renormalized such that:
  $$\sum_{\text{alloy}} w_i = 100.0\%$$

### Step 4: Material Family Matching
The rule engine evaluates each specification in `rule_engine/knowledge/materials.json`:
1. **Required Elements**: If an alloy requires $>17.5\%$ Cr and it is absent, the family compatibility is severely penalized.
2. **Band Limits**: Deviation beyond $[min, max]$ decreases compatibility linearly with slope proportional to element importance.
3. **Ratio Gates**: Evaluates stoichiometric criteria (e.g. $1.80 \le \frac{Cr}{Ni} \le 2.80$).

### Step 5: Component Fingerprint Scoring
Rather than relying on arbitrary neural networks, component identification compares the normalized spectrum against 48 empirical fingerprints built from 171 historical spectra:
- For each alloy element $i$:
  $$z_i = \frac{|x_i - \text{median}_i|}{\text{IQR}_i + \epsilon}$$
- Distance metric incorporates variable importance weights and a $2.50\times$ penalty for foreign elements not characteristic of that component.
- Final compatibility is computed via bounded exponential decay:
  $$\text{Compatibility} = \exp\left(-\frac{\text{Distance}}{k}\right)$$

### Step 6: Conflict Detection
If the analyst entered `Declared Material: 100Cr6`, but the spectrum reveals $18\%\text{ Cr}, 8\%\text{ Ni}$, the system detects an immediate conflict:
- Decision shifts to `conflict`.
- Severity is marked `critical`.
- The UI highlights the discrepancy and prompts the analyst to check for surface plating or sample mix-up.
