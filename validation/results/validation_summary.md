# EDS Prediction Pipeline — Leave-One-Spectrum-Out Validation Report

- **Evaluated Spectra**: 159
- **Unique Components**: 36
- **Execution Time**: 0.08s

## Core Accuracy Metrics

| Metric | Accuracy | Target |
|---|---|---|
| **Family Top-1 Accuracy** | **91.19%** | ≥85% |
| **Component Top-1 Accuracy (All)** | **62.89%** | — |
| **Component Top-1 Accuracy (≥5 spectra)** | **67.9%** | ≥60% |
| **Component Top-3 Accuracy (≥5 spectra)** | **95.06%** | ≥80% |
| **Component Top-5 Accuracy (All)** | **97.48%** | ≥80% |

## Decision Breakdown

- `identified`: 114 (71.7%)
- `ambiguous`: 37 (23.3%)
- `insufficient_data`: 7 (4.4%)
- `unknown`: 1 (0.6%)

## Per-Component Performance (Top Components)

| Component | Spectra | Family Acc | Top-1 Acc | Top-3 Acc |
|---|---|---|---|---|
| M&M HPP Component | 14 | 100% | 100% | 100% |
| CRI Injector Body | 8 | 100% | 25% | 75% |
| Armature Plate | 7 | 100% | 14% | 86% |
| Valve Nut | 7 | 100% | 100% | 100% |
| Armature Bolt | 6 | 83% | 50% | 100% |
| Clamping Saddle | 6 | 100% | 100% | 100% |
| Locking Sleeve | 6 | 100% | 100% | 100% |
| NR Nut | 6 | 100% | 100% | 100% |
| Valve Piece | 6 | 83% | 50% | 83% |
| DFK Shim | 5 | 100% | 40% | 100% |
| Magnet Core | 5 | 0% | 60% | 100% |
| Valve Spring | 5 | 80% | 40% | 100% |
| Armature Guide | 4 | 100% | 0% | 50% |
| Armature Spring | 4 | 25% | 0% | 75% |
| Guide Bush | 4 | 100% | 50% | 100% |
| Magnet Coil | 4 | 75% | 100% | 100% |
| Nozzle Spring | 4 | 100% | 75% | 100% |
| Support Sealing | 4 | 100% | 25% | 100% |
| Valve Piston | 4 | 100% | 100% | 100% |
| VFK Shim | 4 | 100% | 0% | 75% |
