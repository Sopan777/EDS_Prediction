# DHATU BODH (धातु बोध)
### Industrial EDS Material & Component Microanalysis Intelligence

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Django 6.1](https://img.shields.io/badge/Django-6.1-green.svg)](https://www.djangoproject.com/)
[![Standards Compliance](https://img.shields.io/badge/Standards-ASTM%20E1508%20%7C%20ISO%2022309-orange.svg)]()
[![Tests Passing](https://img.shields.io/badge/Tests-139%20passed-brightgreen.svg)]()

**DHATU BODH** is an industrial-grade Energy-Dispersive X-ray Spectroscopy (EDS) microanalysis application engineered for failure analysis, technical cleanliness (VDA 19.1 / ISO 16232), and precision particle identification. It deterministically classifies unknown microscopic debris and alloy specimens into standardized material families and performs empirical component-level matching against 48 statistical fingerprints derived from historical SEM/EDS consolidation datasets.

---

## Key Capabilities

- **Deterministic Material Classification**: Eliminates stochastic black-box AI errors. Enforces international standard concentration bands and stoichiometric ratio gates (ASTM E1508 / ISO 22309).
- **Multi-Spectrum Particle Pooling**: Aggregates multiple measurement spots across a single debris particle to compute arithmetic centroid chemistry and isolate local surface contamination.
- **Empirical Component Fingerprinting**: 48 canonical components characterized by robust non-parametric statistics (medians, IQR dispersion bounds, sample frequency).
- **Metallurgical Conflict Detection**: Automatically cross-references declared specimen metadata (e.g. `100Cr6`) against measured EDS chemistry, alerting analysts to surface plating, conversion coatings, or sample mix-ups.
- **Bosch-Inspired UI Design**: Clean, quiet, structured interface with dark charcoal typography, Bosch red (`#ED0007`) accents, and single primary document scrolling (zero nested scroll traps).
- **Analyst Verification & Feedback Loop**: Captures confirmations and domain corrections to continuously audit system accuracy.
- **Full Traceability**: SQLite persistence logging analysis sessions, feedback events, and configuration modifications (`spectral_lab.db`).

---

## Material Family Taxonomy

| Code | Human-Readable Family Name | Primary Grade Hint | Characteristic Chemistry |
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

## System Architecture & Data Flow

```
[ Ingest Instrument Data ] (PDF, CSV, JSON, TXT, Manual wt%)
            |
            v
[ Metal-Basis Renormalization ] (Strips non-alloy C, O, N, F, Ca, etc.)
            |
            +-------------------------------------------------+
            |                                                 |
            v                                                 v
[ Tier 1: Material Family ]                       [ Tier 2: Component Matching ]
- Concentration bands (materials.json)            - Standardized distance z = |x - med|/IQR
- Stoichiometric gates (Cr/Ni, Cu/Sn, W/Mo)       - 48 empirical fingerprints (171 spectra)
- Safe abstention (UNKNOWN / INSUFFICIENT)        - Foreign element penalty (2.50x)
            |                                                 |
            +-----------------------+-------------------------+
                                    |
                                    v
            [ Metallurgical Conflict & Discrepancy Check ]
            - Compares declared metadata vs measured chemistry
                                    |
                                    v
            [ Prioritized Results Display & Persistence ]
            - 1. Predicted Family (Score & Grade Hint)
            - 2. Top Predicted Component & Quality Badge
            - 3. Composition Breakdown vs Specification Bands
            - 4. Stoichiometric Ratio Gate Verification
            - 5. Alternative Candidates Table
            - 6. Warnings & Conflict Alerts
            - 7. Analyst Feedback & Verification Loop
```

---

## Getting Started

### 1. Prerequisites
- Python 3.10+ (64-bit)
- SQLite3

### 2. Installation
```bash
# Clone the repository
git clone <repository-url>
cd EDS_Prediction

# Set up virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate
```

### 3. Launch the Application
```bash
python manage.py runserver 127.0.0.1:8000
```
Open **http://localhost:8000** in your browser.

---

## Web Navigation Guide

- **Executive Dashboard** (`/` or `/dashboard/`): High-level operational metrics, system integrity indicators, and recent analysis runs.
- **Analyze EDS** (`/analyzer/`): Drag-and-drop report ingestion (PDF/CSV/JSON/TXT), manual composition entry with Fe auto-balance, declared material input, and prioritized 7-step analysis results.
- **Knowledge Base** (`/knowledge/`): 3 interactive tabs for Material Families, Component Library (48 parts), and Stoichiometric Ratio Gates with real-time universal search.
- **Ratio Gate Editor** (`/gates/<family_id>/`): Calibrate threshold limits and technical rationales for deterministic gates.
- **Analysis History & Audit** (`/history/`): Full analysis history, analyst feedback log (confirmations & corrections), and system audit trail.
- **Settings & Reference Data** (`/settings/`): Engine configuration, alloy presets manager, and authorized laboratory personnel roster.
- **Reports & Certificates** (`/reports/`): Formal laboratory characterization certificates compliant with ISO/IEC 17025.

---

## Running Automated Tests

Run the complete test suite using `pytest`:
```bash
pytest tests/ -v
```

All 139 active regression and invariant tests pass:
```
====================== 139 passed, 158 skipped in 1.45s =======================
```

---

## Documentation Suite

Detailed engineering guides are located in the `docs/` directory:

| Document | Description |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Full system topology, Django app layout, services, and security. |
| [docs/setup.md](docs/setup.md) | Step-by-step development and production deployment guide. |
| [docs/prediction-pipeline.md](docs/prediction-pipeline.md) | End-to-end execution trace from raw spectrum to classification. |
| [docs/material-family-engine.md](docs/material-family-engine.md) | Invariants, concentration bands, and deterministic scoring. |
| [docs/component-prediction.md](docs/component-prediction.md) | Empirical fingerprints, standardized distance, and validation results. |
| [docs/knowledge-base.md](docs/knowledge-base.md) | 12 families, 48 components, and ratio gate calibration. |
| [docs/api.md](docs/api.md) | REST API endpoints, schemas, and request/response examples. |
| [docs/frontend.md](docs/frontend.md) | Bosch-inspired UI philosophy, templates, and vanilla JS controllers. |
| [docs/data-model.md](docs/data-model.md) | SQLite database tables, models, and entity relationships. |
| [docs/feedback-system.md](docs/feedback-system.md) | Continuous improvement, analyst confirmation, and retraining loop. |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common issues, error messages, and diagnostic commands. |

---

## License & Compliance

Compliant with ASTM E1508, ISO 22309, and VDA 19.1 standards for particulate contamination and failure analysis. Developed for high-reliability manufacturing microanalysis.
