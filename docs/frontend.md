# DHATU BODH — Frontend Architecture & UI Philosophy

## 1. Design Philosophy

DHATU BODH implements a **Bosch-inspired industrial design language**:
- **Clean & Quiet**: Light neutral canvas (`#f8fafc`), high-contrast dark charcoal typography (`#0f172a`), minimal visual fatigue for long microscopy sessions.
- **Bosch Red Accent (`#ED0007`)**: Used sparingly for key primary actions, live indicators, and critical discrepancies.
- **Single Primary Document Scroll**: Zero nested scroll traps, zero card-in-card vertical clipping, and zero `overflow-hidden` height locking on `<main>`. The entire page scrolls naturally as a cohesive technical document.
- **Honest Hierarchy**: Data is structured in clear, non-nested cards with precise data tables and standard metallurgical labels.

---

## 2. Template Structure

All pages extend `templates/base.html`:
```
templates/
  ├── base.html                  # Core enterprise navbar, footer, modals, brand layout
  ├── analyzer/
  │     ├── dashboard.html       # Executive Dashboard with real metrics & recent runs
  │     └── index.html           # Analyze EDS (ingestion, pooling, 7-step results)
  ├── knowledge/
  │     ├── index.html           # Knowledge Base (Families, 48 Components, Ratio Gates)
  │     └── gates.html           # Ratio Gate calibration & threshold editor
  ├── history/
  │     └── index.html           # Analysis runs, analyst feedback log, system audit trail
  ├── users/
  │     └── index.html           # Settings, rule engine status, alloy presets, personnel
  └── reports/
        └── index.html           # ISO/IEC 17025 certificate archive & printable reports
```

---

## 3. JavaScript Controller Modules

The frontend avoids heavy Single Page App (SPA) dependencies (like React or Vite) to ensure zero build steps and maximum reliability:
- `static/js/analyzer.js`: Controls drag-and-drop file ingestion, multi-spectrum pooling tabs, Fe auto-balancing, and renders results in strict 7-step priority.
- `static/js/knowledge.js`: Powers instant client-side search across material families, 48 empirical components, and stoichiometric gates.
- `static/js/gates.js`: Manages adding, removing, and testing deterministic ratio gates.
- `templates/base.html`: Provides `window.openAppModal` and `window.closeAppModal` for dialogs and detailed inspection views.
