# EDS Material-Family Identification Pipeline

Takes SEM/EDAX elemental composition (weight %) from a particle found in a
Bosch injector — either typed by hand or extracted from a PDF/DOCX Material
analysis report — and identifies the material **family** (plus grade hint and
a ranked list of candidate components), never a single component name.

```
report.pdf/.docx --> eds_geometry --> spectra --> rule_engine.scoring --> family / grade / candidates
```

## Why family, not component

An earlier version of this project predicted one of 36 exact component names
using an ML pipeline and a separate hand-written rule engine. Both are still
present in this repo (`predictor.py`, `models/`, `rule_engine/engine.py`,
`rule_engine/rules/rules.json`) but are **retired as decision authorities**:

- No trained ML model artifacts exist on disk (`saved_models/` is absent), so
  every call into `predictor.py` raises `FileNotFoundError` before a single
  prediction is made.
- The rule engine's `rules.json` was generated from a synthetic dataset that
  turned out to be the reference table plus jitter, with no independent
  measurement information, and a training-time pruning step that deleted
  necessary lower bounds from 30 of 36 rules. Against the six real
  analyst-labelled particles available for this project, it scored 0/5
  correct chemistries — every wrong answer at confidence 1.00.
- Measured directly: on real component centroids, colliding pairs stay
  entirely within one material family at every noise level tested. Exact
  component identity is not recoverable from EDS composition alone; material
  family is.

**Full findings, root causes and the rebuild rationale: [docs/EDS_AUDIT.md](docs/EDS_AUDIT.md).**

The current, working prediction path is `rule_engine/scoring.py` — a
deterministic compatibility engine over a metal-normalised composition basis,
with abstention as a first-class answer. It requires only the Python
standard library.

## Web Application (Django Full-Stack)

The production web interface is powered by a **Django-based full-stack architecture** (Django templates + Django ORM + REST APIs + Tailwind CSS).

### Starting the Server

```bash
# Using Django's management utility
python manage.py runserver 8000

# Or using the root launcher
python server.py
```
Then visit **http://localhost:8000** in your browser.

- **Analyzer Dashboard**: `/` or `/analyzer/` — Real-time microanalysis via manual wt% or PDF/CSV report uploads, automated stoichiometric cross-matching, circular compatibility gauge, candidate component specs.
- **Knowledge Base**: `/knowledge/` — All 12 material families, ASTM element bands, ratio gates, and candidate assemblies.
- **Gate Calibration**: `/gates/<family_id>/` — Live dynamic validation against 1,204 spectra with pass/fail threshold tuning.
- **System Audit Log**: `/history/` — Full traceability, event filtering, and CSV export.
- **Personnel Management**: `/settings/` or `/users/` — Lab analyst roster, privilege management, and activity monitoring.
- **Reports & Certificates**: `/reports/` — Official laboratory analysis records and certificates.
- **REST APIs**: `/api/health`, `/api/families`, `/api/analyze`, `/api/gates`, `/api/audit-logs`, `/api/users`.

---

## Project layout

```
.
├── manage.py                       # Django command-line management utility
├── server.py                       # Root launcher for Django server
├── config/                         # Django project configuration (settings, urls, wsgi)
│   ├── settings.py                 # Core settings, database (spectral_lab.db), apps, static
│   └── urls.py                     # Root URL router & REST API routes
├── apps/                           # Django domain applications
│   ├── analyzer/                   # EDS microanalysis & prediction GUI/APIs
│   ├── knowledge/                  # Metallurgical knowledge base & ratio gate calibration
│   ├── history/                    # Traceability, audit logs & analysis history
│   ├── users/                      # Lab personnel roster & permissions
│   └── reports/                    # Official microanalysis certificates
├── services/                       # Business logic & services layer
│   ├── eds/                        # PDF/CSV extraction wrappers (PyMuPDF)
│   ├── prediction/                 # Deterministic scoring execution
│   ├── knowledge/                  # Knowledge base singleton & formatting
│   └── audit/                      # Centralized audit logging service
├── templates/                      # Django HTML templates (Dark theme, Tailwind CSS)
│   ├── base.html                   # Master layout, navigation, and global modals
│   ├── analyzer/index.html         # Analysis Bento grid view
│   ├── knowledge/index.html        # 1/3 - 2/3 Knowledge Base view
│   ├── knowledge/gates.html        # Ratio gate editor & live validation preview
│   ├── history/index.html          # Audit log table & CSV export
│   ├── users/index.html            # Personnel management & roles
│   └── reports/index.html          # Certificate & report archive
├── static/                         # Static assets
│   ├── css/tailwind.css            # Pre-compiled Tailwind stylesheet
│   └── js/                         # Client-side scripts (main.js, analyzer.js, gates.js, etc.)
├── spectral_lab.db                 # SQLite database (persisting reports, audit, gates, users)
├── requirements.txt                # Python dependencies
├── config.py                       # Central pipeline paths & constants
│
├── rule_engine/                    # Core metallurgical domain engine (stdlib only)
│   ├── elements.py                 # Chemical element symbols & canonicalization
│   ├── real_data.py                # Loads the 173 real spectra from data/EDS Consolidation.xlsx
│   ├── normalize.py                # 3-state missingness, contamination isolation, metal-basis
│   ├── scoring.py                  # Probabilistic log-likelihood scoring, abstention, KnowledgeBase
│   ├── validator.py                # Knowledge base integrity validator
│   ├── knowledge/
│   │   ├── sigma_model.json        # Measurement-uncertainty model fitted from real spectra
│   │   └── materials.json          # Family definitions + element bands (generated)
│   └── rules/                      # Retired conjunctive rules (audit record)
│
├── backend/                        # Backend engines
│   └── ingestion/                  # Document parsing and table extraction
│       ├── eds_geometry.py         # Word-geometry PDF table extractor (PyMuPDF)
│       ├── eds_extractor.py        # Character-offset PDF table extraction fallback
│       ├── docx_to_pdf.py          # DOCX -> PDF conversion utility
│       └── eds_pipeline.py         # Batch report processing pipeline
│
├── data/                           # Ground-truth datasets & sample reports
│   ├── EDS Consolidation.xlsx      # 173 REAL spectra ("Components" sheet) - source of truth
│   ├── EDS Consolidation - Priority.xlsx  # 37-row reference table, one spectrum per component
│   ├── synthetic_eds_data.csv      # Baseline synthetic dataset
│   └── reports/                    # Sample real-world EDS PDF reports
│
├── tests/                          # Automated test suite (all passing)
│   ├── data/real_particles.json    # Ground-truth transcription of 6 real labelled particles
│   ├── test_streamlit_app.py       # Streamlit app endpoints, pipeline & database tests
│   ├── test_real_particles.py      # THE PRIMARY GATE - scores against real particles
│   ├── test_scoring_invariance.py  # Mathematical invariance and negative controls
│   └── test_knowledge_validation.py # Material bounds and schema integrity
│
├── training/                       # Derivation & validation scripts
│   ├── derive_sigma_model.py       # Fits sigma_model.json from real repeat spectra
│   ├── derive_knowledge.py         # Builds materials.json from real spectra + predicates
│   └── validate_loco.py            # Leave-one-component-out validation
│
└── docs/                           # Documentation
    ├── EDS_AUDIT.md                # Full audit: findings, root causes, roadmap
    └── RULE_ENGINE.md              # Architectural specification
```

## Setup

```bash
pip install -r requirements.txt
```

`rule_engine/`, `training/derive_*.py` and `training/validate_loco.py` are
**stdlib-only** and need nothing from `requirements.txt`. That file covers:
PyMuPDF (word-geometry PDF extraction), openpyxl (only needed by the legacy
pandas-based scripts — `rule_engine/real_data.py` reads the workbook with
stdlib `zipfile`), pytest, and the retired ML stack.

## 1. Generate the knowledge base (one-time, or after changing real_data.py)

```bash
python training/derive_sigma_model.py
python training/derive_knowledge.py
```

The first fits `rule_engine/knowledge/sigma_model.json` — per-element
measurement uncertainty as `sigma(x) = max(floor, cv * x)` — from the real
repeat spectra in `data/EDS Consolidation.xlsx`. The second builds
`rule_engine/knowledge/materials.json`: metallurgical family predicates
(standing domain knowledge, not fitted) combined with element bands derived
from those same real spectra. Both files are generated output — edit the
scripts, not the JSON.

## 2. Run the pipeline on a report

```bash
python eds_pipeline.py report.pdf
python eds_pipeline.py report.docx
python eds_pipeline.py report.pdf --per-spectrum
python eds_pipeline.py report.pdf --save-json outputs/report_predictions.json
```

Extracts every composition table in the report (preferring
`eds_geometry.py`'s word-geometry parsing; falling back to the older
character-offset extractor only if PyMuPDF is unavailable) and, per table,
pools every spectrum as repeat measurements of one particle to produce a
family/grade/candidate-list answer. `--per-spectrum` additionally reports each
row individually, useful when one table in fact covers more than one physical
location.

## 3. Use the terminal app directly

```bash
# Interactive mode
python app_rule.py

# Single identification from element values ('-' means analysed, not detected)
python app_rule.py --predict "Cr=17.5,Ni=8.5,Mn=1.5,Si=0.4"

# Batch identification from a JSON file of {element: value} dicts
python app_rule.py --batch spectra.json

# List all known material families
python app_rule.py --list-families

# Element bands, ratio gates and candidate components for one family
python app_rule.py --family-info F4

# Knowledge base info and caveats
python app_rule.py --info
```

## 4. Use the engine in code

```python
from rule_engine.scoring import predict_spectrum, predict_particle

# Fe must be included: the metal basis renormalises the alloy elements to
# 100%, so omitting the matrix element inflates every other one (Cr alone
# would read as >60 wt%) and the composition no longer resembles any real
# reference spectrum.
result = predict_spectrum({"Cr": 18.5, "Ni": 9.5, "Mn": 1.4, "Si": 0.4, "Fe": 68.5})
print(result.decision)               # Decision.IDENTIFIED / AMBIGUOUS / UNKNOWN
print(result.top.label)              # e.g. "Austenitic stainless steel 18/8"
print(result.top.compatibility)      # goodness-of-fit, capped below 1.0 - never a probability
print(result.candidate_components)   # ranked list, scoped to the decision actually given
print(result.caveats)                # e.g. carbon-not-determinable, multi-candidate warnings

# Repeat measurements of ONE particle: evidence is pooled, not voted -
# a family contradicted by any single spectrum is disqualified outright.
pooled = predict_particle([
    {"Cr": 18.5, "Ni": 9.5, "Mn": 1.4, "Si": 0.4, "Fe": 68.5},
    {"Cr": 18.8, "Ni": 9.8, "Mn": 1.5, "Si": 0.4, "Fe": 68.0},
])
```

A value of `None`, `"-"`, or an omitted key all mean different things and are
treated differently:

- **key omitted** → `NOT_ANALYSED`. No information; reduces evidence
  sufficiency but never confirms or contradicts a family.
- **value is `None` / `"-"` / `"n/a"`, key present in `analysed_elements`** →
  `BELOW_LOD`. Positive evidence of absence; can contradict a family that
  requires the element.
- **a real number** → `MEASURED`.

Collapsing these three states into a single `0.0` — as the retired engine
did — is why `{"S": 0.2}` used to match "Guide Bush" at confidence 1.00
despite Guide Bush's every reference spectrum carrying 1.12–1.60 wt% Mn.

## Running tests

```bash
pytest tests/ -v                       # current engine: primary gate + invariance + validation
pytest tests/ -v --run-legacy          # also run the quarantined legacy suite (retired engine)
python training/validate_loco.py       # leave-one-component-out: the honest generalisation number
```

The legacy suite is skipped by default because its `known_class_samples`
fixture used to select a sample only if the (retired) engine already
predicted it correctly — making 36 of its tests unable to fail regardless of
the engine's real behaviour. It has been repaired to select samples
unconditionally; run it with `--run-legacy` to see the real per-class
accuracy of the retired engine (it now correctly fails on the classes it is
actually bad at).

`tests/test_real_particles.py` is the primary gate: it scores against a
hand-verified transcription of the six real analyst-labelled particles in the
Material analysis report PDFs — the only real labelled ground truth available
for this project.

## Notes / caveats

- **Carbon content is not determinable by EDS** (light element; carbon-tape
  and mounting-medium background). Every prediction says so explicitly, and
  no family may be described as a specific carbon grade.
- **Compatibility is a goodness-of-fit statistic, not a probability.** It is
  capped at 0.95. With only six real labelled particles, no honest
  probability calibration is possible.
- **Abstention and ambiguous sets are first-class answers**, not failure
  modes — this mirrors how the source reports themselves are written (a
  chemistry class plus a *list* of probable sources, sometimes marked with
  the analyst's own `??`).
- See [docs/EDS_AUDIT.md](docs/EDS_AUDIT.md) for the full audit: every root
  cause, the leave-one-component-out validation results (99.3% family
  accuracy), the edge-case matrix, and what data is still needed before
  component-level prediction would be defensible.
