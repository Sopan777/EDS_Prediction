# DHATU BODH — System Architecture

## 1. Overview
**DHATU BODH** is an enterprise-grade Energy-Dispersive X-ray Spectroscopy (EDS) microanalysis and material identification application. It deterministically classifies unknown microscopic debris, particles, and alloy specimens into standardized material families (e.g. Bearing Steels, Austenitic Stainless Steels, Tool Steels, Bronzes) and performs empirical component-level matching against statistical fingerprints.

The application follows the **ASTM E1508** (Standard Guide for Quantitative Analysis by Energy-Dispersive Spectroscopy) and **ISO 22309** (Quantitative analysis using energy dispersive spectrometry) specifications.

---

## 2. High-Level Architecture

```
+-----------------------------------------------------------------------------------+
|                                DHATU BODH Web UI                                  |
|   (Django Server-Rendered Templates + Tailwind CSS + Vanilla JS Controller Core)  |
|                                                                                   |
|  [ Dashboard ]   [ Analyze EDS ]   [ Knowledge Base ]   [ History ]  [ Settings ] |
+-----------------------------------------------------------------------------------+
                                         |
                                         | JSON API & Form POST
                                         v
+-----------------------------------------------------------------------------------+
|                               Django Web Application                              |
|                                                                                   |
|   apps/analyzer/    apps/knowledge/    apps/history/    apps/users/   apps/feedback |
|     views.py          views.py           views.py         views.py      views.py  |
+-----------------------------------------------------------------------------------+
         |                        |                          |
         v                        v                          v
+------------------+    +-------------------+    +----------------------------------+
| Ingestion Layer  |    | Prediction Engine |    | Persistence Layer                |
| (services/eds/)  |    | (services/        |    | (SQLite / spectral_lab.db)       |
|                  |    |  prediction/)     |    |                                  |
|  - PyMuPDF PDF   |    |                   |    |  - AnalysisHistory               |
|    geometry      |    |  - Pooled Particle|    |  - PredictionFeedback            |
|  - CSV/JSON/TXT  |    |  - Decision Logic |    |  - AuditLog                      |
|    parsers       |    |  - History Logger |    |  - RatioGate                     |
+------------------+    +-------------------+    |  - AlloyPreset                   |
                                  |              |  - UserAccount                   |
                                  v              +----------------------------------+
+-----------------------------------------------------------------------------------+
|                         Core Deterministic Rule Engine                            |
|                                (rule_engine/)                                     |
|                                                                                   |
|  1. normalize.py          : Metal-basis renormalization (excluding C, O, N, etc.) |
|  2. scoring.py            : Specification bands & deterministic ratio gates       |
|  3. component_scoring.py  : Standardized distance z = |x - median| / IQR           |
|  4. conflict_detector.py  : Declared material metadata vs measured chemistry      |
|  5. knowledge/            : Empirical fingerprints (48 components, 171 spectra)   |
+-----------------------------------------------------------------------------------+
```

---

## 3. Django App Topology

The codebase is organized into focused, single-responsibility Django apps:

| App Directory | Responsibilities | Key Endpoints |
|---|---|---|
| `apps/analyzer/` | Particle ingestion, manual wt% input, multi-spectrum pooling, execution of prediction pipeline. | `GET /`, `GET /analyzer/`, `POST /api/analyze`, `GET /api/components` |
| `apps/knowledge/` | Specification taxonomy, nominal elemental bands, stoichiometric ratio gate calibration. | `GET /knowledge/`, `GET /gates/<fid>/`, `GET /api/families`, `PUT /api/gates/<fid>` |
| `apps/history/` | Traceability audit trail, past analysis session records, export handlers. | `GET /history/`, `GET /api/history`, `GET/POST /api/audit-logs` |
| `apps/feedback/` | Analyst verification feedback loop, confirmation/correction capture. | `GET /api/feedback`, `POST /api/feedback` |
| `apps/users/` | Laboratory personnel registry, access permissions, system calibration settings. | `GET /settings/`, `GET/POST /api/users` |
| `apps/reports/` | ISO/IEC 17025 certificate generation and printable summaries. | `GET /reports/`, `GET/POST /api/reports` |

---

## 4. Service and Computation Layer

### `services/eds/extractor.py`
Ingests diverse spectrometer file outputs. For PDF documents (e.g. Oxford Instruments AZtec or Thermo Phenom), it uses `backend/ingestion/eds_geometry.py` and PyMuPDF bounding-box geometry extraction to parse tabular element wt% results without OCR errors. It also provides clean parsers for CSV, TXT, JSON, and Excel data files.

### `services/prediction/engine.py`
Orchestrates prediction:
1. Validates and aggregates multiple spectra for a single particle if pooling is enabled.
2. Invokes `rule_engine.scoring.predict_particle` or `predict_spectrum`.
3. Runs `rule_engine.component_scoring.rank_components` to identify the best component fit.
4. Detects conflicts with any declared metadata via `rule_engine.conflict_detector`.
5. Persists the analysis session into `AnalysisHistory` in `spectral_lab.db`.

---

## 5. Security & Isolation

1. **No External Cloud Dependency**: All prediction calculations, fingerprint distances, and PDF extractions execute strictly on-premise inside the local Python runtime.
2. **CSRF Protection**: All mutating endpoints (`POST`, `PUT`, `DELETE`) require Django CSRF verification or standard token headers.
3. **Auditability**: Every modification to ratio gates or user roles writes an immutable audit record to `AuditLog`.
