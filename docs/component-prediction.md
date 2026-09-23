# DHATU BODH — Component Prediction & Fingerprinting

This document describes the empirical component fingerprinting system and robust standardized distance scoring (`rule_engine/component_scoring.py`).

---

## 1. Motivation

While material family identification (e.g. `F2 Low-Alloy Chromium Bearing Steel`) narrows down the metallurgical specification, engineering failure analysts need to know the exact component part (e.g. *Armature Bolt* vs *Bearing Ring* vs *Needle Roller* vs *Delivery Valve*).

Because components made of the same nominal alloy share similar elemental bands, traditional thresholding fails to distinguish between them. **DHATU BODH** solves this by generating non-parametric statistical fingerprints from historical EDS reference datasets.

---

## 2. Statistical Fingerprint Architecture

Each component fingerprint (`rule_engine/knowledge/component_fingerprints.json`) stores non-parametric dispersion statistics calculated on metal-basis normalized spectra:

For each detected alloy element:
- **Median ($Q_2$)**: Robust central tendency indicator.
- **25th Percentile ($Q_1$) & 75th Percentile ($Q_3$)**: Bound the interquartile range.
- **Interquartile Range ($\text{IQR} = Q_3 - Q_1$)**: Robust measure of statistical dispersion that is impervious to detector outliers.
- **Frequency of Observation ($f$)**: Proportion of historical spectra containing this element. Classified into:
  - `expected` ($f \ge 0.80$)
  - `common` ($0.20 \le f < 0.80$)
  - `rare` ($f < 0.20$)
- **Sample Count ($n$)**: Number of historical reference spectra available.

### Fingerprint Quality Tiers
- **HIGH Quality**: $n \ge 20$ spectra (tight confidence intervals).
- **MEDIUM Quality**: $5 \le n < 20$ spectra.
- **LOW Quality**: $1 \le n < 5$ spectra (flagged in the UI to encourage caution).

---

## 3. Standardized Distance Formulation

Given an unknown normalized spectrum $x$, the standardized distance to a candidate component fingerprint is computed as:

$$z_i = \frac{|x_i - \text{median}_i|}{\text{IQR}_i + \epsilon}$$

where $\epsilon = 0.10$ prevents division by zero for elements with tight bounds.

### Element Weighting:
Not all elements are equally discriminating. Weight $w_i$ is assigned based on role and element importance:
- Core alloying markers (e.g. $Cr$ in bearing steel, $W, Mo, V$ in tool steel): $w_i = 1.50$
- Secondary alloy elements ($Mn, Si$): $w_i = 1.00$
- Common impurities: $w_i = 0.50$

### Foreign Element Penalty:
If the unknown spectrum exhibits an element with $x_j > 0.50\text{ wt}\%$ that was historically classified as `rare` or never observed in that component, a heavy penalty is applied:
$$\text{Penalty}_j = 2.50 \times \left(1.0 + \frac{x_j}{2.0}\right)$$

### Aggregated Distance & Compatibility:
$$\text{Total Distance} = \frac{\sum_i w_i z_i}{\sum_i w_i} + \sum_j \text{Penalty}_j$$

$$\text{Compatibility} = \text{Evidence Sufficiency} \times \exp\left(-\frac{\text{Total Distance}}{8.0}\right)$$

where $\text{Evidence Sufficiency}$ represents the fraction of `expected` elements present in the test spectrum.

---

## 4. Cross-Validation Results

The system was validated using Leave-One-Spectrum-Out cross-validation across all 171 reference spectra (`validation/leave_one_out.py`):
- **Material Family Top-1 Accuracy**: **91.19%**
- **Component Top-1 Accuracy ($n \ge 5$)**: **67.9%**
- **Component Top-3 Accuracy ($n \ge 5$)**: **95.06%**
