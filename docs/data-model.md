# DHATU BODH — Database Model & Schema Reference

DHATU BODH stores persistent session records, ratio gates, audit events, and user accounts in SQLite (`spectral_lab.db`).

---

## 1. Schema Diagram

```
+-----------------------------------+        +-----------------------------------+
|          AnalysisHistory          |        |        PredictionFeedback         |
+-----------------------------------+        +-----------------------------------+
| id (PK, VARCHAR)                  |        | id (PK, VARCHAR)                  |
| timestamp (VARCHAR)               |        | timestamp (VARCHAR)               |
| source_type (VARCHAR)             |        | analysis_id (FK, VARCHAR, opt)    |
| filename (VARCHAR, opt)           |        | spectrum_json (TEXT)              |
| composition_json (TEXT)           |        | predicted_family (VARCHAR)        |
| decision (VARCHAR)                |        | predicted_component (VARCHAR)     |
| material_family (VARCHAR)         |        | confirmed_family (VARCHAR)        |
| grade_hint (VARCHAR)              |        | confirmed_component (VARCHAR)     |
| compatibility (FLOAT)             |        | status ('confirmed'|'corrected')  |
| candidates_json (TEXT)            |        | analyst_name (VARCHAR)            |
| processing_time_s (FLOAT)         |        | notes (TEXT)                      |
+-----------------------------------+        +-----------------------------------+

+-----------------------------------+        +-----------------------------------+
|             AuditLog              |        |             RatioGate             |
+-----------------------------------+        +-----------------------------------+
| id (PK, VARCHAR)                  |        | id (PK, VARCHAR)                  |
| timestamp (VARCHAR)               |        | family_id (VARCHAR)               |
| user (VARCHAR)                    |        | name (VARCHAR)                    |
| user_role (VARCHAR)               |        | numerator (VARCHAR)               |
| action (TEXT)                     |        | denominator (VARCHAR)             |
| action_type (VARCHAR)             |        | min_val (FLOAT)                   |
| entity_id (VARCHAR)               |        | max_val (FLOAT)                   |
| change_details_json (TEXT)        |        | rationale (TEXT)                  |
| impact_type ('positive'|'neutral')|        | enabled (INTEGER)                 |
+-----------------------------------+        | updated_at (VARCHAR)              |
                                             | updated_by (VARCHAR)              |
+-----------------------------------+        +-----------------------------------+
|            UserAccount            |
+-----------------------------------+        +-----------------------------------+
| id (PK, VARCHAR)                  |        |            AlloyPreset            |
| name (VARCHAR)                    |        +-----------------------------------+
| email (VARCHAR)                   |        | id (PK, VARCHAR)                  |
| role (VARCHAR)                    |        | name (VARCHAR)                    |
| department (VARCHAR)              |        | category (VARCHAR)                |
| permissions (VARCHAR)             |        | description (TEXT)                |
| is_active (INTEGER)               |        | composition_json (TEXT)           |
| created_at (VARCHAR)              |        | created_by (VARCHAR)              |
+-----------------------------------+        | created_at (VARCHAR)              |
                                             +-----------------------------------+
```

---

## 2. Models Detail

### `AnalysisHistory` (`apps/history/models.py`)
Persists every microanalysis execution. `composition_json` stores the raw input composition, and `candidates_json` stores ranked candidate components with their statistical distance scores.

### `PredictionFeedback` (`apps/feedback/models.py`)
Captures analyst verification loops. Distinguishes whether the engineer **confirmed** the predicted result or logged a **correction** with domain notes.

### `RatioGate` (`apps/knowledge/models.py`)
Stores user-customized stoichiometric ratio gates. Overrides or supplements hardcoded gates from `rule_engine/knowledge/materials.json`.

### `AlloyPreset` (`apps/knowledge/models.py`)
Defines standard reference alloy compositions that analysts can load with a single click in the Analyzer UI.

### `AuditLog` (`apps/history/models.py`)
Maintains an immutable record of system changes (gate adjustments, calibration updates, role promotions) satisfying ISO/IEC 17025 traceability requirements.
