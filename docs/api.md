# DHATU BODH — REST API Reference

DHATU BODH provides a RESTful JSON API for programmatic integration with laboratory spectrometers, automated particle counters, and external LIMS (Laboratory Information Management Systems).

---

## 1. Health & Status

### `GET /api/health`
Returns the operational health and configuration state of the prediction engine.

**Response `200 OK`:**
```json
{
  "status": "ok",
  "version": "2.4.0",
  "rule_engine": "deterministic_compatibility_scoring",
  "knowledge_base_loaded": true,
  "families_count": 12,
  "pdf_ingest_available": true,
  "framework": "Django 6.1"
}
```

---

## 2. Microanalysis & Prediction

### `POST /api/analyze`
Executes single-point or pooled multi-spectrum prediction.

#### A. Single Spectrum Manual Input:
```json
{
  "composition": {
    "Fe": 97.5,
    "Cr": 1.5,
    "Mn": 0.35,
    "Si": 0.25
  },
  "declared_material": "100Cr6"
}
```

#### B. Multi-Spectrum Pooled Particle:
```json
{
  "spectra": [
    { "Fe": 97.4, "Cr": 1.52, "Mn": 0.36 },
    { "Fe": 97.6, "Cr": 1.48, "Mn": 0.34 }
  ],
  "declared_material": "Sl2 B1"
}
```

#### C. File Upload:
Send `multipart/form-data` with `file=@report.pdf` or `file=@spectrum.csv`.

**Response `200 OK`:**
```json
{
  "analysisId": "an-1727025624102",
  "decision": "identified",
  "materialFamily": "Low-alloy Cr bearing steel",
  "familyCode": "F2",
  "gradeHint": "100Cr6 / Sl2 B1 / SAE 52100",
  "compatibilityPct": 95,
  "topCandidate": {
    "name": "Armature Bolt",
    "component_id": "ARMATURE_BOLT",
    "confidence": 95,
    "fingerprintQuality": "MEDIUM",
    "sampleCount": 6,
    "evidenceSufficiency": 1.0,
    "notes": "Statistical match to Armature Bolt reference fingerprint..."
  },
  "candidateComponents": [...],
  "ratioGates": [...],
  "conflict": {
    "has_conflict": false,
    "severity": "none"
  },
  "processingTime": "0.02s"
}
```

---

## 3. Knowledge Base Endpoints

### `GET /api/families`
Returns list of all material families and their concentration bands.

### `GET /api/components`
Returns list of all 48 empirical components with their quality badges.

### `GET /api/components/<component_id>`
Returns complete non-parametric statistical fingerprint for a specific component (medians, IQR, percentiles per element).

### `GET /api/gates/<family_id>`
Returns active ratio gates for a family.

### `PUT /api/gates/<family_id>`
Updates ratio gates for a family.

---

## 4. Analyst Feedback

### `POST /api/feedback`
Submits an analyst verification or correction to the audit feedback loop.

**Request Body:**
```json
{
  "analysis_id": "an-1727025624102",
  "spectrum": { "Fe": 97.5, "Cr": 1.5 },
  "predicted_family": "Low-alloy Cr bearing steel",
  "predicted_component": "Armature Bolt",
  "confirmed_family": "Low-alloy Cr bearing steel",
  "confirmed_component": "Armature Bolt",
  "status": "confirmed",
  "analyst_name": "Lead Metallurgist",
  "notes": "Verified bulk microstructure."
}
```

### `GET /api/feedback`
Returns list of logged feedback entries.
