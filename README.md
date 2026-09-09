# Spectral-Lab MaterialID — integrated with EDS_Prediction

One application: an uploaded EDS report is extracted automatically and
scored by a deterministic **Rule-Based Engine** against an editable
**Knowledge Base**, surfaced through the Spectral-Lab UI.

```
Spectral-Lab UI (frontend/)  <-- HTTP -->  FastAPI (backend/)  --calls-->  eds_core/ (unmodified)
                                                                              ├─ eds_pipeline.py      (PDF -> tables)
                                                                              ├─ eds_extractor.py     (extraction)
                                                                              └─ rule_engine/
                                                                                  ├─ normalize.py      (cleaning)
                                                                                  ├─ scoring.py         (Rule-Based Engine)
                                                                                  └─ knowledge/materials.json  (Knowledge Base)
```

## Directory layout

- `eds_core/` — your original EDS_Prediction project, **unmodified**. The
  Rule-Based Engine (`rule_engine/scoring.py` + `rule_engine/knowledge/materials.json`)
  and the extraction pipeline (`eds_pipeline.py`, `eds_extractor.py`) are the
  ones actually used. `models/`, `predictor.py`, `train_all_models.py` (the
  ML path) are left in place but are never imported by the backend.
- `backend/` — new FastAPI web layer. Thin adapters over `eds_core`:
  - `analyze_service.py` — PDF/manual -> extraction -> normalization -> Rule-Based Engine
  - `kb_service.py` — Knowledge Base read/write, with validation + backups,
    and live cache-invalidation of the rule engine on every save
  - `audit.py` — persisted audit log
  - `main.py` — the API routes + serves the built frontend
- `frontend/` — the Spectral-Lab UI, now on **Next.js** (App Router,
  static export) instead of Vite. Its mock data was already replaced by
  calls to the backend (`frontend/src/api/client.ts`), plus a new
  **Knowledge Base Editor** screen. All the original components/state
  logic live under `frontend/src/`; `frontend/app/` is just the thin
  Next.js entry point (`layout.tsx` + `page.tsx`) that mounts `src/App.tsx`.
- `samples/` — the 3 sample EDS PDFs, used by `/api/samples/*`.
- `data_store/` — runtime state: `audit_log.json`, `kb_backups/` (auto
  timestamped backup written before every Knowledge Base save), `uploads/`.
- `tests/test_backend_e2e.py` — automated end-to-end tests (pytest), covering
  every sample PDF, manual analysis, KB CRUD + validation, and audit logging.

## Running it

```bash
# 1. Backend deps (rule-based only — no ML packages)
pip install -r requirements.txt --break-system-packages

# 2. Build the frontend once (Next.js static export -> frontend/out/)
cd frontend && npm install && npm run build && cd ..

# 3. Run the whole app (backend serves the exported static site at /)
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 — this is the one unified app (analyzer,
knowledge base, KB editor, audit log, all in the Spectral-Lab UI).

For frontend development with hot reload instead of the built export:
```bash
# terminal 1
uvicorn backend.main:app --reload --port 8000
# terminal 2
cd frontend && npm run dev   # next dev; /api/* rewritten to :8000, per next.config.js
```
Note: the dev-time `rewrites()` in `next.config.js` only apply under
`next dev` (a live dev server). They're a no-op — with a harmless build
warning — once you run `next build` with `output: 'export'`, because a
static export has no server to run rewrites on. In the exported/production
setup the frontend and backend are already same-origin (both served by
FastAPI on :8000), so no proxy is needed there at all.

## Tests

```bash
pytest tests/test_backend_e2e.py -v
```
Runs the complete PDF → extraction → Rule-Based Engine flow against all 3
bundled sample reports, plus KB CRUD/validation and audit logging.

## How each requirement was met

1. **Rule-Based only** — `backend/analyze_service.py` imports only
   `rule_engine.scoring`. No CatBoost/RandomForest/XGBoost/ExtraTrees
   import exists anywhere in the backend or its call graph.
2. **PDF → extraction → cleaning → Rule Engine → prediction** —
   `backend/analyze_service.analyze_pdf()` calls `eds_core/eds_pipeline.run_pipeline()`
   unchanged, which already chains extraction, `rule_engine.normalize`, and
   `rule_engine.scoring`.
3. **Reused, not reimplemented** — the scoring logic, checks, and
   Knowledge Base live entirely in `eds_core/rule_engine/`; the backend only
   adapts shapes for the UI.
4. **Spectral-Lab as main frontend** — `frontend/` is the Spectral-Lab app;
   its navigation, analyzer, knowledge-base and audit-log screens are all
   preserved, with a new "Knowledge Base Editor" screen added the same way.
5. **KB drives predictions, live** — `backend/kb_service.py` reads/writes
   `eds_core/rule_engine/knowledge/materials.json` directly, and invalidates
   `rule_engine.scoring`'s cached copy after every save — verified in
   `tests/test_backend_e2e.py::test_knowledge_base_crud_round_trip_and_engine_reload`.
6. **Knowledge Base Editor** — `frontend/src/components/KnowledgeBaseEditorView.tsx`:
   view/add/edit/delete families, element bands, ratio gates and candidate
   components; `Validate` calls `rule_engine.validator.validate_knowledge_base`
   before any write reaches disk (`POST /api/knowledge-base/validate`).
7. **Analyzer fields** — `AnalyzerView.tsx` shows extracted elements +
   validation status, matched rules/families with individual checks, the
   predicted component, a clearly-labeled **Rule-Based Score**, the reason
   string from the engine, and an explicit Unknown/No Match state.
8. **Modular, non-breaking** — `eds_core/` is untouched; the backend only
   imports it, it never edits its source.
9. **ML disabled, not deleted** — `eds_core/models/`, `predictor.py`,
   `train_all_models.py`, `compare_models.py` remain on disk but are not
   imported by `backend/` or referenced by any active route.
10. **Tested end-to-end** — `tests/test_backend_e2e.py` exercises all three
    sample PDFs plus manual entry, KB CRUD, and audit logging; all pass.
