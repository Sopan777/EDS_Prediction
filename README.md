# Spectral Lab — Integrated EDS Microanalysis & Material-Family Identification Platform

An integrated, production-grade web application for SEM/EDAX energy-dispersive X-ray spectroscopy (EDS) microanalysis. The system ingests raw laboratory reports (PDF, DOCX, CSV, JSON) or manual elemental concentrations (wt%) and determines the material **family**, metallurgical grade hint, and candidate injector components using a deterministic compatibility scoring engine and persistent database.

---

## Complete Application Pipeline

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Laboratory Input Sources                        │
│  - PDF Material Reports (multi-table, word-level bounding-box geometry)│
│  - Word Documents (.docx / .doc auto-converted to vector PDF)          │
│  - Chemical Data (.csv, .json tables)                                  │
│  - Manual wt% Entry via Interactive Chemical Keyboard UI               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             Stage 1: Document Ingestion & Table Extraction             │
│                 (backend/ingestion/eds_geometry.py)                     │
│  - PyMuPDF word-level geometry extraction for EDS spectrum tables      │
│  - Multi-column alignment and elemental symbol canonicalization        │
│  - Isolate contaminant elements (C, O, N, F)                           │
│  - Normalise alloy elements to 100% metal basis                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│            Stage 2: Deterministic Compatibility Rule Engine            │
│                       (rule_engine/scoring.py)                         │
│  - 3-state missingness: MEASURED vs BELOW_LOD vs NOT_ANALYSED          │
│  - Measurement uncertainty model: sigma(x) = max(floor, cv * x)        │
│  - Multi-spectrum evidence pooling via predict_particle()              │
│  - Dynamic injection of user-configured ratio gates from SQLite        │
│  - Safe abstention (UNKNOWN) when decisive alloy signals are absent    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│            Stage 3: SQLite Persistent Storage & Audit Trail            │
│                       (backend/server.py)                              │
│  - analysis_history: Stores all analyses, inputs, decisions & timings  │
│  - uploaded_files: Permanent storage in uploads/ with metadata         │
│  - ratio_gates: Live user overrides that directly steer scoring        │
│  - audit_logs: Full provenance of gate modifications and scans         │
│  - sessions: Particle scanning session tracking                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                Stage 4: React Modern Web Application                   │
│                            (frontend/)                                 │
│  - Microanalysis Dashboard: live SVG gauge, candidate ranking, caveats │
│  - Knowledge Base: 12 metallurgical families, elemental bands, ranges  │
│  - Ratio Gate Editor: boundary tuning with real centroid validation    │
│  - Analysis History: searchable archive with decision badges & filters │
│  - Laboratory User & Access Management                                 │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start (One-Click Launch)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the Application
```bash
python run_app.py
```

`run_app.py` automatically:
- Checks frontend dependencies and runs `npm install` if required.
- Builds the production Vite bundle if `frontend/dist/` is missing.
- Initializes the SQLite database (`spectral_lab.db`).
- Launches the Flask web server on `http://localhost:5000`.
- Opens your default web browser automatically.

To run on a custom port without automatically opening a browser:
```bash
python run_app.py --port 8080 --no-browser
```

---

## Application Structure

```
.
├── run_app.py                      # Single integrated application launcher
├── config.py                       # Paths, database, and uploads configuration
├── requirements.txt                # Production Python dependencies
├── .env.example                    # Environment variable template
│
├── backend/                        # Backend web services & document ingestion
│   ├── server.py                   # Production Flask REST API & static SPA server
│   └── ingestion/                  # Document parsing and table extraction
│       ├── eds_geometry.py         # Word-geometry PDF table extractor (PyMuPDF)
│       ├── docx_to_pdf.py          # DOCX/DOC converter (Word COM / LibreOffice)
│       └── eds_pipeline.py         # Multi-table pooled analysis pipeline
│
├── frontend/                       # React 19 + TypeScript + Vite + Tailwind UI
│   ├── src/
│   │   ├── App.tsx                 # Root application container & live data loaders
│   │   ├── types.ts                # Domain TypeScript interfaces
│   │   ├── components/
│   │   │   ├── AnalyzerView.tsx        # Particle analysis, file dropzone & gauges
│   │   │   ├── KnowledgeBaseView.tsx   # Material family library & elemental bands
│   │   │   ├── RatioGateEditorView.tsx # Gate configuration & real validation preview
│   │   │   ├── AnalysisHistoryView.tsx # Searchable history of all past analyses
│   │   │   ├── SettingsView.tsx        # System settings, diagnostics & audit trace
│   │   │   └── Navigation.tsx          # Responsive navigation & theme toggles
│   ├── package.json
│   └── vite.config.ts
│
├── rule_engine/                    # Core metallurgical domain engine (stdlib-only)
│   ├── scoring.py                  # Likelihood scoring, abstention, KnowledgeBase
│   ├── normalize.py                # Metal-basis renormalization & 3-state missingness
│   ├── elements.py                 # Chemical element symbols & canonicalization
│   ├── real_data.py                # Direct reader for the 173 reference spectra
│   ├── validator.py                # Schema & boundary integrity validator
│   └── knowledge/
│       ├── materials.json          # 12 metallurgical family definitions & bands
│       └── sigma_model.json        # Fitted measurement-uncertainty model
│
├── data/                           # Reference datasets & sample reports
│   ├── EDS Consolidation.xlsx      # 173 reference spectra from Bosch components
│   └── reports/                    # Real-world laboratory PDF reports for testing
│
└── tests/                          # Automated verification suite (125 tests passing)
    ├── test_server_fixes.py        # Regression tests for API contracts & gates
    ├── test_e2e_real_pdf.py        # End-to-end PDF upload & ingestion test
    ├── test_spectral_lab_web.py    # REST API endpoints & static serving tests
    ├── test_real_particles.py      # Ground-truth tests against labelled particles
    ├── test_scoring_invariance.py  # Invariance against carbon, oxidation & scale
    └── test_knowledge_validation.py# Materials knowledge base boundary tests
```

---

## Configuration & Environment Variables

Configure application settings by copying `.env.example` to `.env`:

| Variable | Default | Description |
|---|---|---|
| `PORT` | `5000` | Port the Flask application listens on |
| `FLASK_ENV` | `production` | Set to `development` for Flask debug mode |
| `DATABASE_URL` | `sqlite:///spectral_lab.db` | SQLite database URI or path |
| `UPLOADS_DIR` | `./uploads` | Directory for uploaded EDS reports |

---

## REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health, version, loaded families, and subsystem availability |
| `GET` | `/api/families` | Returns all 12 material families with real bands and ratio gates |
| `GET` | `/api/families/<fid>` | Detail for a single family (`F4`, `F1a`, etc.) |
| `POST` | `/api/analyze` | Predict material family from manual wt% or file upload (PDF/DOCX/CSV/JSON) |
| `GET` | `/api/analyses` | List stored historical analyses with pagination and search |
| `GET` | `/api/analyses/<aid>` | Detailed result of a specific historical analysis |
| `POST` | `/api/sessions` | Create and track a particle scan session |
| `GET` | `/api/gates` | List ratio gates for a family (including active SQLite overrides) |
| `PUT` | `/api/gates/<fid>` | Update and persist ratio gates for a family |
| `POST` | `/api/gates/validate` | Test gate configuration against real reference centroids |
| `GET` | `/api/audit-logs` | Retrieve chronological audit logs |
| `POST` | `/api/audit-logs` | Record an audit entry |
| `GET` | `/api/users` | List active laboratory users |
| `POST` | `/api/users` | Add a new laboratory user |
| `PUT` | `/api/users/<uid>` | Update user role, department, or permissions |
| `GET` | `/` | Serves the compiled React single-page application |

---

## Metallurgical Domain Principles

1. **Material Family, Never Exact Component**: Colliding component pairs share identical bulk chemistry (e.g., Guide Bush vs. CRI Injector Body). Exact component names cannot be deterministically deduced from EDS alone; material families (e.g., plain carbon steel, austenitic stainless steel) can.
2. **Metal-Basis Renormalization**: Foreign organic contamination (carbon tape, mounting epoxy, surface oxidation) is isolated by renormalizing remaining alloy elements (Fe, Cr, Ni, Mn, Si, Mo, Cu, etc.) to a 100% metal basis.
3. **Three-State Missingness**:
   - `MEASURED`: An element detected with positive concentration.
   - `BELOW_LOD`: An element explicitly analysed but below the detection limit (negative evidence).
   - `NOT_ANALYSED`: An element omitted from the scan spectrometer configuration (no evidence).
4. **Multi-Spectrum Evidence Pooling**: Multiple spectra from different spots on the same particle are combined via log-likelihood pooling. A single contradicting spectrum definitively disqualifies an incompatible family.
5. **Safe Abstention as a First-Class Result**: When an EDS spectrum does not exhibit decisive alloy markers (e.g., pure iron with trace silicon), the engine abstains (`UNKNOWN`) to prevent confident misclassifications.

---

## Testing & Verification

Run the full automated test suite (125 tests):
```bash
pytest tests/ -v
```

### Test Coverage Highlights:
- **`tests/test_real_particles.py`**: Scores against ground-truth analyst transcriptions of real particle PDFs (100% agreement).
- **`tests/test_server_fixes.py`**: Validates unclamped compatibility scores, real candidate component names, live SQLite ratio gate injection, and history endpoints.
- **`tests/test_e2e_real_pdf.py`**: End-to-end integration test of actual PDF report ingestion, PyMuPDF extraction, and database persistence.
- **`tests/test_scoring_invariance.py`**: Verifies mathematical invariance against oxidation, carbon tape background, scale, and element order.
- **`tests/test_knowledge_validation.py`**: Verifies schema integrity, band validity, and ratio gate constraints in `materials.json`.
