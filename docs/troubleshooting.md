# DHATU BODH — Troubleshooting & FAQ

This document addresses common operational issues, error codes, and diagnostic procedures.

---

## 1. Common Issues & Solutions

### Issue A: "No valid elemental spectra could be extracted"
- **Cause**: Input spectrum had 0 wt% for all elements, or an unsupported file format was uploaded.
- **Solution**: Ensure at least one metallic element ($Fe, Cr, Ni, Mn, Si, Cu, Sn$) has non-zero concentration. For PDF files, verify that the document contains vector text tables rather than scanned low-resolution raster images.

### Issue B: Prediction returns `UNKNOWN` or `INSUFFICIENT_DATA`
- **Cause**: The input spectrum does not match any reference specification in `rule_engine/knowledge/materials.json` (e.g. pure Titanium, Lead solder, or heavy non-metallic dust).
- **Solution**: Check whether non-metallic contamination (C, O, N) dominates the spectrum. If the specimen is an uncataloged custom alloy, check the Knowledge Base or add a new material specification in `materials.json`.

### Issue C: `METALLURGICAL CONFLICT` alert displayed
- **Cause**: The `Declared Material` entered in metadata contradicts the measured EDS chemistry (e.g. declaring `100Cr6` bearing steel for an `AISI 304` stainless steel particle).
- **Solution**: Check if surface plating (e.g. Zn galvanized or Au flash) was scanned rather than the bulk alloy substrate, or verify if sample labeling was switched during SEM mounting.

### Issue D: Port 8000 already in use
- **Cause**: Another process or background instance is occupying port 8000.
- **Solution**:
  - Windows: `netstat -ano | findstr :8000` followed by `taskkill /F /PID <pid>`
  - Linux/Mac: `lsof -i :8000` followed by `kill -9 <pid>`
  - Or start Django on a custom port: `python manage.py runserver 8080`

---

## 2. Diagnostic Commands

Verify engine and database health:
```bash
python manage.py shell -c "from services.knowledge.kb import get_kb; from rule_engine.component_fingerprints import load_fingerprints; print('Engine KB OK:', get_kb() is not None); print('Fingerprints loaded:', len(load_fingerprints()))"
```

Verify test suite integrity:
```bash
pytest tests/ -v
```
