# DHATU BODH — Knowledge Base Guide

The Knowledge Base forms the reference core of DHATU BODH, combining international metallurgical standards with empirical manufacturing data.

---

## 1. Structure

The Knowledge Base is divided into three interconnected layers:
1. **Material Families** (`rule_engine/knowledge/materials.json`): Standard alloy families, nominal concentration bands, grade hints, and required element gates.
2. **Component Library** (`rule_engine/knowledge/component_fingerprints.json`): 48 canonical components with empirical medians, IQR bands, sample counts, and nominal material bodies.
3. **Stoichiometric Ratio Gates** (`apps/knowledge/models.py` & `materials.json`): Quantitative physical ratio gates enforcing phase stability boundaries.

---

## 2. Canonical Components (48 Parts)

Below is an excerpt of key empirical components mapped in the library:

| Component ID | Display Name | Nominal Alloy | Reference Quality | Sample Count ($n$) |
|---|---|---|---|---|
| `ARMATURE_BOLT` | Armature Bolt | 100Cr6 (F2) | MEDIUM | 6 |
| `BACKING_RING` | Backing Ring | 100Cr6 (F2) | LOW | 4 |
| `BALL_BEARING` | Ball Bearing | 100Cr6 (F2) | HIGH | 22 |
| `CRI_SEALING_RING` | CRI Sealing Ring | CuSn8 (F6a) | HIGH | 25 |
| `DELIVERY_VALVE` | Delivery Valve | High-Speed Tool Steel (F3) | MEDIUM | 8 |
| `NEEDLE_ROLLER` | Needle Roller | 100Cr6 (F2) | HIGH | 20 |
| `PLUNGER` | Plunger | Case-Hardening Steel (F1b) | MEDIUM | 12 |
| `SPRING_WASHER` | Spring Washer | Silicon-Chromium Steel (F1c) | MEDIUM | 14 |
| `VALVE_SEAT` | Valve Seat | Austenitic 18/8 (F4) | MEDIUM | 15 |

---

## 3. Ratio Gate Management & Calibration

Analysts with *Chief Metallurgist* privileges can adjust ratio gates directly in the Web UI (`/gates/<fid>/`):
- **Numerator & Denominator**: Elements being evaluated (e.g. $Cr / Ni$).
- **Allowed Thresholds**: Minimum and maximum boundaries.
- **Metallurgical Rationale**: Technical reason for the gate (e.g. *Prevents misclassifying duplex stainless grades*).
- **Audit Logging**: Every edit automatically records a change event in the `AuditLog` table.
