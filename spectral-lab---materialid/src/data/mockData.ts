import { MaterialFamily, UserAccount, RoleDefinition, AuditLogEntry } from '../types';

export const METAL_MACRO_BG = 'https://lh3.googleusercontent.com/aida-public/AB6AXuDSOwYihuS6a1ZvQjHgaqy-vX02LBa-6BVsIx58BXCECLJkatLtGIW3ENEnMjmnIIDwnkNh701uudmD-qLlhC1NIAgfFSsOFeT81sKgEy28ZpZ4a3IawEEecHF-0OW2lbLBaF5iMZarh5hLpvZn10J4qMRnVOmUyj09OUGYmPmNZ_-iJZaW_B4iyZlOey966mjvFoqXokJv0xAw_mnGMmDtxBwxgVyqPmdtRSXIbT6SYmtw9PLG2Fhy';
export const AVATAR_THORNE = 'https://lh3.googleusercontent.com/aida-public/AB6AXuDiApSUwVh7spJDQqxtoJArf_tgebm8wP2A-Ciu-m0nRUr8zGpLzfotTH95U7w1vNH9QPAaBKpey4566K3OR1pU2rEhcdez-Gg6EBpZasQDha0_y4d_WdIo2Kd2JnSHYEgyZCjsUfYxhLRIO-qbFDqJ07QMeISDdZVfEjE5IlIq3JgUVtY55FyvvoZvjTk7oxjo7gMg17Uqg5ZIi8DnZCixmV2Hqi8gadyV0R1jp_e93XBq2nYW6hcw';
export const AVATAR_EYE = 'https://lh3.googleusercontent.com/aida-public/AB6AXuDSbP2L1UDuoS6fHl1LH4btxkos4R1FzyyDYHijTMb201xXi1M8_bOyQVclgk6PpBs8Zi7bJUZjDVmbPWdwzuH-42dlTlMbJAfVtVb1TdiAFWb0u1PklI-qg--T_hLliz0EDes5SRmaWlljmJ-sWWmsCUh89Febq1y4IH5thBd8zgGklCrjPozYMxdTsQKsLPLAwBxUz65BgWmvLZ00c4d9BpE2v6KMZXRZN4ihkmSfoR62KlOmwdxv';
export const AVATAR_ORB = 'https://lh3.googleusercontent.com/aida-public/AB6AXuC0Yk-GcAQ1HBnIFPHPSCANUpzN55fAHug59CAgOPKf_IPEI3u-LSB671jo3o3BalGlMHVSwpnMVz9SUzchk2ivRxM1OhWzh9mMZSJpXIcbra-5M2sB9nOx0RRhwBgU6YjHZuLStAL6F8FEOWDpobCnjV3hCo89nDbeL9veQprc2t-pUBB3trKGCOHYEUsDWa59Fy4Vc7VXwseyNeXxupUKVHzIZlkQy6R9gctg7cPt696-sSOU_ol-';
export const LOGO_ABSTRACT = 'https://lh3.googleusercontent.com/aida-public/AB6AXuDLZTylPha9n67BPYXFbldtqrFt-RslqwW3yCMuQ__szsbVIQvwlGcgjQj1PtvGk2LmMLXSbYFrk7rmhRJEDidJkvFtZ738GauZrTmwQr59Y9N-qPCWU68pggjybf8b9UCkebMy4ilrCOgt9rYNiPNZjd-f0FmQ7_HW1O3atWPAx1OHFA7CbDCv1v0uUbGnCbZX6gZzBn0d-xOSIP3m_hrZDQJjKDbSEFzIVgLkH3s0EvFcWFyXuqEF';

export const INITIAL_MATERIAL_FAMILIES: MaterialFamily[] = [
  {
    "id": "f4-austenitic",
    "code": "F4",
    "name": "Austenitic stainless steel 18/8",
    "gradeHint": "X8CrNiS18-9 / X12CrNiS19-8",
    "status": "FIRM",
    "description": "Requires BOTH Cr and Ni at alloy level. If either was not analysed this family is unevaluable, never a match - the failure that produced 'Magnet housing' for a plain 1.5Mn steel.",
    "compatibilityScore": 95,
    "totalSpectra": 120,
    "passingSpectra": 117,
    "failingSpectra": 3,
    "elementBands": [
      {
        "element": "Cr",
        "role": "Required",
        "rangeMin": 14.26,
        "rangeMax": 24.37,
        "spectraSupport": 10,
        "barOffsetPct": 47,
        "barWidthPct": 33
      },
      {
        "element": "Fe",
        "role": "Required",
        "rangeMin": 65.4,
        "rangeMax": 71.3,
        "spectraSupport": 10,
        "barOffsetPct": 65,
        "barWidthPct": 8
      },
      {
        "element": "Mn",
        "role": "Optional",
        "rangeMin": 0.74,
        "rangeMax": 2.11,
        "spectraSupport": 9,
        "barOffsetPct": 2,
        "barWidthPct": 8
      },
      {
        "element": "Mo",
        "role": "Optional",
        "rangeMin": 0.45,
        "rangeMax": 1.51,
        "spectraSupport": 2,
        "barOffsetPct": 1,
        "barWidthPct": 8
      },
      {
        "element": "Ni",
        "role": "Required",
        "rangeMin": 7.44,
        "rangeMax": 13.12,
        "spectraSupport": 10,
        "barOffsetPct": 24,
        "barWidthPct": 18
      },
      {
        "element": "S",
        "role": "Optional",
        "rangeMin": 0.15,
        "rangeMax": 0.54,
        "spectraSupport": 2,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "Si",
        "role": "Required",
        "rangeMin": 0.07,
        "rangeMax": 0.78,
        "spectraSupport": 10,
        "barOffsetPct": 0,
        "barWidthPct": 8
      }
    ],
    "ratioGates": [
      {
        "id": "gate-f4-1",
        "name": "Cr/Ni",
        "numerator": "Cr",
        "denominator": "Ni",
        "min": 1.4,
        "max": 3.2,
        "rationale": "18/8 austenitic stoichiometry; observed 1.6-2.2 in real spectra.",
        "enabled": true
      }
    ],
    "candidateComponents": [
      {
        "id": "comp-F4-back-flow-tube",
        "name": "Back Flow Tube",
        "partNumber": "BOSCH-F4-BFT42",
        "category": "Precision Subcomponent",
        "nominalAlloy": "X8CrNiS18-9 / X12CrNiS19-8",
        "confidence": 95,
        "notes": "Observed reference component for F4 (Austenitic stainless steel 18/8)."
      },
      {
        "id": "comp-F4-locking-sleeve",
        "name": "Locking Sleeve",
        "partNumber": "BOSCH-F4-LS42",
        "category": "Precision Subcomponent",
        "nominalAlloy": "X8CrNiS18-9 / X12CrNiS19-8",
        "confidence": 95,
        "notes": "Observed reference component for F4 (Austenitic stainless steel 18/8)."
      },
      {
        "id": "comp-F4-magnet-housing",
        "name": "Magnet housing",
        "partNumber": "BOSCH-F4-MH42",
        "category": "Precision Subcomponent",
        "nominalAlloy": "X8CrNiS18-9 / X12CrNiS19-8",
        "confidence": 95,
        "notes": "Observed reference component for F4 (Austenitic stainless steel 18/8)."
      }
    ],
    "contextCaveats": [
      {
        "title": "Carbon untracked",
        "description": "C content not reliably determinable via standard EDS.",
        "icon": "warning"
      },
      {
        "title": "Renormalized",
        "description": "Metal-basis renormalized excluding O, C, N, F.",
        "icon": "calculate"
      },
      {
        "title": "Metallurgical note",
        "description": "Requires BOTH Cr and Ni at alloy level. If either was not analysed this family is unevaluable, never a match - the failure that produced 'Magnet housing' for a plain 1.5Mn steel.",
        "icon": "info"
      }
    ]
  },
  {
    "id": "f1a-plain",
    "code": "F1a",
    "name": "Plain / low-Mn carbon steel",
    "gradeHint": "plain C steel, C45PbK, En1A and similar",
    "status": "FIRM",
    "description": "The largest and least specific family. Many components share it, so component identity is not recoverable here by composition alone.",
    "compatibilityScore": 95,
    "totalSpectra": 732,
    "passingSpectra": 717,
    "failingSpectra": 15,
    "elementBands": [
      {
        "element": "Al",
        "role": "Trace",
        "rangeMin": 0.0,
        "rangeMax": 1.47,
        "spectraSupport": 23,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "Cr",
        "role": "Optional",
        "rangeMin": 0.0,
        "rangeMax": 0.8,
        "spectraSupport": 36,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "Fe",
        "role": "Required",
        "rangeMin": 96.59,
        "rangeMax": 100.63,
        "spectraSupport": 61,
        "barOffsetPct": 96,
        "barWidthPct": 4
      },
      {
        "element": "Mn",
        "role": "Optional",
        "rangeMin": 0.0,
        "rangeMax": 1.18,
        "spectraSupport": 56,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "Pb",
        "role": "Trace",
        "rangeMin": 0.0,
        "rangeMax": 0.5,
        "spectraSupport": 8,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "S",
        "role": "Optional",
        "rangeMin": 0.0,
        "rangeMax": 0.19,
        "spectraSupport": 4,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "Si",
        "role": "Optional",
        "rangeMin": 0.0,
        "rangeMax": 1.36,
        "spectraSupport": 50,
        "barOffsetPct": 0,
        "barWidthPct": 8
      }
    ],
    "ratioGates": [],
    "candidateComponents": [
      {
        "id": "comp-F1a-armature-shim",
        "name": "Armature Shim",
        "partNumber": "BOSCH-F1a-AS39",
        "category": "Precision Subcomponent",
        "nominalAlloy": "plain C steel, C45PbK, En1A and similar",
        "confidence": 95,
        "notes": "Observed reference component for F1a (Plain / low-Mn carbon steel)."
      },
      {
        "id": "comp-F1a-cri-injector-body",
        "name": "CRI Injector Body",
        "partNumber": "BOSCH-F1a-CIB51",
        "category": "Fuel Injector Assembly",
        "nominalAlloy": "plain C steel, C45PbK, En1A and similar",
        "confidence": 95,
        "notes": "Observed reference component for F1a (Plain / low-Mn carbon steel)."
      },
      {
        "id": "comp-F1a-cri-shim",
        "name": "CRI Shim",
        "partNumber": "BOSCH-F1a-CS24",
        "category": "Precision Subcomponent",
        "nominalAlloy": "plain C steel, C45PbK, En1A and similar",
        "confidence": 95,
        "notes": "Observed reference component for F1a (Plain / low-Mn carbon steel)."
      },
      {
        "id": "comp-F1a-dfk-shim",
        "name": "DFK Shim",
        "partNumber": "BOSCH-F1a-DS24",
        "category": "Precision Subcomponent",
        "nominalAlloy": "plain C steel, C45PbK, En1A and similar",
        "confidence": 95,
        "notes": "Observed reference component for F1a (Plain / low-Mn carbon steel)."
      },
      {
        "id": "comp-F1a-dfk-spring",
        "name": "DFK Spring",
        "partNumber": "BOSCH-F1a-DS30",
        "category": "Precision Subcomponent",
        "nominalAlloy": "plain C steel, C45PbK, En1A and similar",
        "confidence": 95,
        "notes": "Observed reference component for F1a (Plain / low-Mn carbon steel)."
      },
      {
        "id": "comp-F1a-dowel-pin",
        "name": "Dowel Pin",
        "partNumber": "BOSCH-F1a-DP27",
        "category": "Precision Subcomponent",
        "nominalAlloy": "plain C steel, C45PbK, En1A and similar",
        "confidence": 95,
        "notes": "Observed reference component for F1a (Plain / low-Mn carbon steel)."
      },
      {
        "id": "comp-F1a-ic-stud",
        "name": "IC Stud",
        "partNumber": "BOSCH-F1a-IS21",
        "category": "Precision Subcomponent",
        "nominalAlloy": "plain C steel, C45PbK, En1A and similar",
        "confidence": 95,
        "notes": "Observed reference component for F1a (Plain / low-Mn carbon steel)."
      },
      {
        "id": "comp-F1a-m&m-hpp-component",
        "name": "M&M HPP Component",
        "partNumber": "BOSCH-F1a-MHC51",
        "category": "Precision Subcomponent",
        "nominalAlloy": "plain C steel, C45PbK, En1A and similar",
        "confidence": 95,
        "notes": "Observed reference component for F1a (Plain / low-Mn carbon steel)."
      },
      {
        "id": "comp-F1a-magnet-core",
        "name": "Magnet Core",
        "partNumber": "BOSCH-F1a-MC33",
        "category": "Precision Subcomponent",
        "nominalAlloy": "plain C steel, C45PbK, En1A and similar",
        "confidence": 95,
        "notes": "Observed reference component for F1a (Plain / low-Mn carbon steel)."
      },
      {
        "id": "comp-F1a-rls-shim",
        "name": "RLS Shim",
        "partNumber": "BOSCH-F1a-RS24",
        "category": "Precision Subcomponent",
        "nominalAlloy": "plain C steel, C45PbK, En1A and similar",
        "confidence": 95,
        "notes": "Observed reference component for F1a (Plain / low-Mn carbon steel)."
      },
      {
        "id": "comp-F1a-sealing-ring",
        "name": "Sealing Ring",
        "partNumber": "BOSCH-F1a-SR36",
        "category": "Precision Subcomponent",
        "nominalAlloy": "plain C steel, C45PbK, En1A and similar",
        "confidence": 95,
        "notes": "Observed reference component for F1a (Plain / low-Mn carbon steel)."
      },
      {
        "id": "comp-F1a-support-sealing",
        "name": "Support Sealing",
        "partNumber": "BOSCH-F1a-SS45",
        "category": "Precision Subcomponent",
        "nominalAlloy": "plain C steel, C45PbK, En1A and similar",
        "confidence": 95,
        "notes": "Observed reference component for F1a (Plain / low-Mn carbon steel)."
      },
      {
        "id": "comp-F1a-ufk-spring",
        "name": "UFK Spring",
        "partNumber": "BOSCH-F1a-US30",
        "category": "Precision Subcomponent",
        "nominalAlloy": "plain C steel, C45PbK, En1A and similar",
        "confidence": 95,
        "notes": "Observed reference component for F1a (Plain / low-Mn carbon steel)."
      },
      {
        "id": "comp-F1a-vfk-shim",
        "name": "VFK Shim",
        "partNumber": "BOSCH-F1a-VS24",
        "category": "Precision Subcomponent",
        "nominalAlloy": "plain C steel, C45PbK, En1A and similar",
        "confidence": 95,
        "notes": "Observed reference component for F1a (Plain / low-Mn carbon steel)."
      },
      {
        "id": "comp-F1a-valve-nut",
        "name": "Valve Nut",
        "partNumber": "BOSCH-F1a-VN27",
        "category": "Fuel Injector Assembly",
        "nominalAlloy": "plain C steel, C45PbK, En1A and similar",
        "confidence": 95,
        "notes": "Observed reference component for F1a (Plain / low-Mn carbon steel)."
      }
    ],
    "contextCaveats": [
      {
        "title": "Carbon untracked",
        "description": "C content not reliably determinable via standard EDS.",
        "icon": "warning"
      },
      {
        "title": "Renormalized",
        "description": "Metal-basis renormalized excluding O, C, N, F.",
        "icon": "calculate"
      },
      {
        "title": "Metallurgical note",
        "description": "The largest and least specific family. Many components share it, so component identity is not recoverable here by composition alone.",
        "icon": "info"
      }
    ]
  },
  {
    "id": "f1b-~1.5",
    "code": "F1b",
    "name": "~1.5 Mn plain carbon steel",
    "gradeHint": "16MnCr5-family / 1.5Mn steel",
    "status": "FIRM",
    "description": "Separated from F1a only by Mn. The boundary is ~1.7 sigma on within-component scatter, so it needs an ambiguity band, not a cut.",
    "compatibilityScore": 95,
    "totalSpectra": 100,
    "passingSpectra": 98,
    "failingSpectra": 2,
    "elementBands": [
      {
        "element": "Fe",
        "role": "Required",
        "rangeMin": 97.32,
        "rangeMax": 99.14,
        "spectraSupport": 7,
        "barOffsetPct": 97,
        "barWidthPct": 3
      },
      {
        "element": "Mn",
        "role": "Required",
        "rangeMin": 0.89,
        "rangeMax": 2.16,
        "spectraSupport": 7,
        "barOffsetPct": 2,
        "barWidthPct": 8
      },
      {
        "element": "S",
        "role": "Optional",
        "rangeMin": 0.09,
        "rangeMax": 0.36,
        "spectraSupport": 4,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "Si",
        "role": "Optional",
        "rangeMin": 0.0,
        "rangeMax": 0.44,
        "spectraSupport": 4,
        "barOffsetPct": 0,
        "barWidthPct": 8
      }
    ],
    "ratioGates": [],
    "candidateComponents": [
      {
        "id": "comp-F1b-guide-bush",
        "name": "Guide Bush",
        "partNumber": "BOSCH-F1b-GB30",
        "category": "Precision Subcomponent",
        "nominalAlloy": "16MnCr5-family / 1.5Mn steel",
        "confidence": 95,
        "notes": "Observed reference component for F1b (~1.5 Mn plain carbon steel)."
      },
      {
        "id": "comp-F1b-m&m-hpp-component",
        "name": "M&M HPP Component",
        "partNumber": "BOSCH-F1b-MHC51",
        "category": "Precision Subcomponent",
        "nominalAlloy": "16MnCr5-family / 1.5Mn steel",
        "confidence": 95,
        "notes": "Observed reference component for F1b (~1.5 Mn plain carbon steel)."
      }
    ],
    "contextCaveats": [
      {
        "title": "Carbon untracked",
        "description": "C content not reliably determinable via standard EDS.",
        "icon": "warning"
      },
      {
        "title": "Renormalized",
        "description": "Metal-basis renormalized excluding O, C, N, F.",
        "icon": "calculate"
      },
      {
        "title": "Metallurgical note",
        "description": "Separated from F1a only by Mn. The boundary is ~1.7 sigma on within-component scatter, so it needs an ambiguity band, not a cut.",
        "icon": "info"
      }
    ]
  },
  {
    "id": "f1c-si-cr",
    "code": "F1c",
    "name": "Si-Cr spring steel",
    "gradeHint": "VDSiCr / DIN 17223",
    "status": "FIRM",
    "description": "Elevated Si with only residual Cr.",
    "compatibilityScore": 95,
    "totalSpectra": 204,
    "passingSpectra": 199,
    "failingSpectra": 5,
    "elementBands": [
      {
        "element": "Al",
        "role": "Trace",
        "rangeMin": 0.11,
        "rangeMax": 0.63,
        "spectraSupport": 1,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "Cr",
        "role": "Required",
        "rangeMin": 0.44,
        "rangeMax": 1.02,
        "spectraSupport": 17,
        "barOffsetPct": 1,
        "barWidthPct": 8
      },
      {
        "element": "Fe",
        "role": "Required",
        "rangeMin": 95.53,
        "rangeMax": 98.24,
        "spectraSupport": 17,
        "barOffsetPct": 95,
        "barWidthPct": 5
      },
      {
        "element": "Mn",
        "role": "Optional",
        "rangeMin": 0.22,
        "rangeMax": 0.96,
        "spectraSupport": 15,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "S",
        "role": "Optional",
        "rangeMin": 0.0,
        "rangeMax": 0.14,
        "spectraSupport": 2,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "Si",
        "role": "Required",
        "rangeMin": 0.47,
        "rangeMax": 3.03,
        "spectraSupport": 17,
        "barOffsetPct": 1,
        "barWidthPct": 8
      }
    ],
    "ratioGates": [],
    "candidateComponents": [
      {
        "id": "comp-F1c-armature-spring",
        "name": "Armature Spring",
        "partNumber": "BOSCH-F1c-AS45",
        "category": "Precision Subcomponent",
        "nominalAlloy": "VDSiCr / DIN 17223",
        "confidence": 95,
        "notes": "Observed reference component for F1c (Si-Cr spring steel)."
      },
      {
        "id": "comp-F1c-dfk-spring",
        "name": "DFK Spring",
        "partNumber": "BOSCH-F1c-DS30",
        "category": "Precision Subcomponent",
        "nominalAlloy": "VDSiCr / DIN 17223",
        "confidence": 95,
        "notes": "Observed reference component for F1c (Si-Cr spring steel)."
      },
      {
        "id": "comp-F1c-nozzle-spring",
        "name": "Nozzle Spring",
        "partNumber": "BOSCH-F1c-NS39",
        "category": "Precision Subcomponent",
        "nominalAlloy": "VDSiCr / DIN 17223",
        "confidence": 95,
        "notes": "Observed reference component for F1c (Si-Cr spring steel)."
      },
      {
        "id": "comp-F1c-ufk-spring",
        "name": "UFK Spring",
        "partNumber": "BOSCH-F1c-US30",
        "category": "Precision Subcomponent",
        "nominalAlloy": "VDSiCr / DIN 17223",
        "confidence": 95,
        "notes": "Observed reference component for F1c (Si-Cr spring steel)."
      },
      {
        "id": "comp-F1c-valve-spring",
        "name": "Valve Spring",
        "partNumber": "BOSCH-F1c-VS36",
        "category": "Precision Subcomponent",
        "nominalAlloy": "VDSiCr / DIN 17223",
        "confidence": 95,
        "notes": "Observed reference component for F1c (Si-Cr spring steel)."
      }
    ],
    "contextCaveats": [
      {
        "title": "Carbon untracked",
        "description": "C content not reliably determinable via standard EDS.",
        "icon": "warning"
      },
      {
        "title": "Renormalized",
        "description": "Metal-basis renormalized excluding O, C, N, F.",
        "icon": "calculate"
      },
      {
        "title": "Metallurgical note",
        "description": "Elevated Si with only residual Cr.",
        "icon": "info"
      }
    ]
  },
  {
    "id": "f2-low-alloy",
    "code": "F2",
    "name": "Low-alloy Cr bearing steel",
    "gradeHint": "100Cr6 / Sl2 B1",
    "status": "FIRM",
    "description": "Cr ~1.3-1.9 with low Mn. Carbon content is not determinable by EDS.",
    "compatibilityScore": 95,
    "totalSpectra": 372,
    "passingSpectra": 364,
    "failingSpectra": 8,
    "elementBands": [
      {
        "element": "Al",
        "role": "Trace",
        "rangeMin": 0.0,
        "rangeMax": 0.99,
        "spectraSupport": 7,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "Cr",
        "role": "Required",
        "rangeMin": 1.11,
        "rangeMax": 2.29,
        "spectraSupport": 31,
        "barOffsetPct": 3,
        "barWidthPct": 8
      },
      {
        "element": "Fe",
        "role": "Required",
        "rangeMin": 96.19,
        "rangeMax": 98.82,
        "spectraSupport": 31,
        "barOffsetPct": 96,
        "barWidthPct": 4
      },
      {
        "element": "Mn",
        "role": "Optional",
        "rangeMin": 0.12,
        "rangeMax": 0.72,
        "spectraSupport": 22,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "Ni",
        "role": "Optional",
        "rangeMin": 0.27,
        "rangeMax": 0.74,
        "spectraSupport": 1,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "S",
        "role": "Optional",
        "rangeMin": 0.0,
        "rangeMax": 0.17,
        "spectraSupport": 3,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "Si",
        "role": "Optional",
        "rangeMin": 0.04,
        "rangeMax": 0.61,
        "spectraSupport": 28,
        "barOffsetPct": 0,
        "barWidthPct": 8
      }
    ],
    "ratioGates": [],
    "candidateComponents": [
      {
        "id": "comp-F2-armature-bolt",
        "name": "Armature Bolt",
        "partNumber": "BOSCH-F2-AB39",
        "category": "Precision Subcomponent",
        "nominalAlloy": "100Cr6 / Sl2 B1",
        "confidence": 95,
        "notes": "Observed reference component for F2 (Low-alloy Cr bearing steel)."
      },
      {
        "id": "comp-F2-armature-guide",
        "name": "Armature Guide",
        "partNumber": "BOSCH-F2-AG42",
        "category": "Precision Subcomponent",
        "nominalAlloy": "100Cr6 / Sl2 B1",
        "confidence": 95,
        "notes": "Observed reference component for F2 (Low-alloy Cr bearing steel)."
      },
      {
        "id": "comp-F2-armature-plate",
        "name": "Armature Plate",
        "partNumber": "BOSCH-F2-AP42",
        "category": "Precision Subcomponent",
        "nominalAlloy": "100Cr6 / Sl2 B1",
        "confidence": 95,
        "notes": "Observed reference component for F2 (Low-alloy Cr bearing steel)."
      },
      {
        "id": "comp-F2-ball-guide",
        "name": "Ball Guide",
        "partNumber": "BOSCH-F2-BG30",
        "category": "Precision Subcomponent",
        "nominalAlloy": "100Cr6 / Sl2 B1",
        "confidence": 95,
        "notes": "Observed reference component for F2 (Low-alloy Cr bearing steel)."
      },
      {
        "id": "comp-F2-c-shim",
        "name": "C Shim",
        "partNumber": "BOSCH-F2-CS18",
        "category": "Precision Subcomponent",
        "nominalAlloy": "100Cr6 / Sl2 B1",
        "confidence": 95,
        "notes": "Observed reference component for F2 (Low-alloy Cr bearing steel)."
      },
      {
        "id": "comp-F2-pille",
        "name": "Pille",
        "partNumber": "BOSCH-F2-P15",
        "category": "Precision Subcomponent",
        "nominalAlloy": "100Cr6 / Sl2 B1",
        "confidence": 95,
        "notes": "Observed reference component for F2 (Low-alloy Cr bearing steel)."
      },
      {
        "id": "comp-F2-valve-piece",
        "name": "Valve Piece",
        "partNumber": "BOSCH-F2-VP33",
        "category": "Precision Subcomponent",
        "nominalAlloy": "100Cr6 / Sl2 B1",
        "confidence": 95,
        "notes": "Observed reference component for F2 (Low-alloy Cr bearing steel)."
      }
    ],
    "contextCaveats": [
      {
        "title": "Carbon untracked",
        "description": "C content not reliably determinable via standard EDS.",
        "icon": "warning"
      },
      {
        "title": "Renormalized",
        "description": "Metal-basis renormalized excluding O, C, N, F.",
        "icon": "calculate"
      },
      {
        "title": "Metallurgical note",
        "description": "Cr ~1.3-1.9 with low Mn. Carbon content is not determinable by EDS.",
        "icon": "info"
      }
    ]
  },
  {
    "id": "f3-tool",
    "code": "F3",
    "name": "Tool / high-speed steel",
    "gradeHint": "HSS M2 / Sl2b17 (S6-5-2)",
    "status": "PROV",
    "description": "W-Mo-V carbide formers are decisive and near-unique in this domain. W/Mo is a tight fingerprint (1.47-1.58 on all 4 real spectra) but rests on a single component - provisional, not a hard cut.",
    "compatibilityScore": 85,
    "totalSpectra": 100,
    "passingSpectra": 98,
    "failingSpectra": 2,
    "elementBands": [
      {
        "element": "Cr",
        "role": "Required",
        "rangeMin": 3.57,
        "rangeMax": 5.83,
        "spectraSupport": 4,
        "barOffsetPct": 11,
        "barWidthPct": 8
      },
      {
        "element": "Fe",
        "role": "Required",
        "rangeMin": 75.52,
        "rangeMax": 83.25,
        "spectraSupport": 4,
        "barOffsetPct": 75,
        "barWidthPct": 8
      },
      {
        "element": "Mn",
        "role": "Optional",
        "rangeMin": 0.17,
        "rangeMax": 0.53,
        "spectraSupport": 1,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "Mo",
        "role": "Required",
        "rangeMin": 1.48,
        "rangeMax": 8.98,
        "spectraSupport": 4,
        "barOffsetPct": 4,
        "barWidthPct": 25
      },
      {
        "element": "Ni",
        "role": "Optional",
        "rangeMin": 0.17,
        "rangeMax": 0.66,
        "spectraSupport": 3,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "V",
        "role": "Required",
        "rangeMin": 1.39,
        "rangeMax": 3.59,
        "spectraSupport": 4,
        "barOffsetPct": 4,
        "barWidthPct": 8
      },
      {
        "element": "W",
        "role": "Required",
        "rangeMin": 2.91,
        "rangeMax": 13.1,
        "spectraSupport": 4,
        "barOffsetPct": 9,
        "barWidthPct": 33
      }
    ],
    "ratioGates": [
      {
        "id": "gate-f3-1",
        "name": "W/Mo",
        "numerator": "W",
        "denominator": "Mo",
        "min": 1.1,
        "max": 2.0,
        "rationale": "Observed 1.47-1.58 on all 4 real spectra of the one component behind this family; widened generously since it rests on a single component and should not be treated as a hard cut.",
        "enabled": true
      }
    ],
    "candidateComponents": [
      {
        "id": "comp-F3-valve-piston",
        "name": "Valve Piston",
        "partNumber": "BOSCH-F3-VP36",
        "category": "Precision Subcomponent",
        "nominalAlloy": "HSS M2 / Sl2b17 (S6-5-2)",
        "confidence": 85,
        "notes": "Observed reference component for F3 (Tool / high-speed steel)."
      }
    ],
    "contextCaveats": [
      {
        "title": "Carbon untracked",
        "description": "C content not reliably determinable via standard EDS.",
        "icon": "warning"
      },
      {
        "title": "Renormalized",
        "description": "Metal-basis renormalized excluding O, C, N, F.",
        "icon": "calculate"
      },
      {
        "title": "Metallurgical note",
        "description": "W-Mo-V carbide formers are decisive and near-unique in this domain. W/Mo is a tight fingerprint (1.47-1.58 on all 4 real spectra) but rests on a single component - provisional, not a hard cut.",
        "icon": "info"
      }
    ]
  },
  {
    "id": "f5-ni-base",
    "code": "F5",
    "name": "Ni-base alloy",
    "gradeHint": "Ni-Cr alloy",
    "status": "PROV",
    "description": "Ni is the matrix, not an addition.",
    "compatibilityScore": 85,
    "totalSpectra": 100,
    "passingSpectra": 98,
    "failingSpectra": 2,
    "elementBands": [
      {
        "element": "Al",
        "role": "Trace",
        "rangeMin": 0.0,
        "rangeMax": 4.41,
        "spectraSupport": 4,
        "barOffsetPct": 0,
        "barWidthPct": 14
      },
      {
        "element": "Cr",
        "role": "Required",
        "rangeMin": 0.58,
        "rangeMax": 4.52,
        "spectraSupport": 6,
        "barOffsetPct": 1,
        "barWidthPct": 13
      },
      {
        "element": "Fe",
        "role": "Required",
        "rangeMin": 4.47,
        "rangeMax": 13.18,
        "spectraSupport": 6,
        "barOffsetPct": 14,
        "barWidthPct": 29
      },
      {
        "element": "Ni",
        "role": "Required",
        "rangeMin": 76.28,
        "rangeMax": 99.48,
        "spectraSupport": 6,
        "barOffsetPct": 76,
        "barWidthPct": 23
      }
    ],
    "ratioGates": [],
    "candidateComponents": [
      {
        "id": "comp-F5-clamping-saddle",
        "name": "Clamping Saddle",
        "partNumber": "BOSCH-F5-CS45",
        "category": "Precision Subcomponent",
        "nominalAlloy": "Ni-Cr alloy",
        "confidence": 85,
        "notes": "Observed reference component for F5 (Ni-base alloy)."
      }
    ],
    "contextCaveats": [
      {
        "title": "Carbon untracked",
        "description": "C content not reliably determinable via standard EDS.",
        "icon": "warning"
      },
      {
        "title": "Renormalized",
        "description": "Metal-basis renormalized excluding O, C, N, F.",
        "icon": "calculate"
      },
      {
        "title": "Metallurgical note",
        "description": "Ni is the matrix, not an addition.",
        "icon": "info"
      }
    ]
  },
  {
    "id": "f6a-cu-sn",
    "code": "F6a",
    "name": "Cu-Sn bronze / Cu-Sn metal matrix composite",
    "gradeHint": "CuSn8 and similar",
    "status": "FIRM",
    "description": "Sn/Cu is the stable fingerprint; absolute Cu is unreliable because the seal-ring matrix is PTFE-loaded and dilutes every metal reading.",
    "compatibilityScore": 95,
    "totalSpectra": 100,
    "passingSpectra": 98,
    "failingSpectra": 2,
    "elementBands": [
      {
        "element": "Cr",
        "role": "Optional",
        "rangeMin": 0.8,
        "rangeMax": 1.19,
        "spectraSupport": 1,
        "barOffsetPct": 2,
        "barWidthPct": 8
      },
      {
        "element": "Cu",
        "role": "Required",
        "rangeMin": 29.7,
        "rangeMax": 134.46,
        "spectraSupport": 3,
        "barOffsetPct": 29,
        "barWidthPct": 71
      },
      {
        "element": "Fe",
        "role": "Required",
        "rangeMin": 0.13,
        "rangeMax": 21.75,
        "spectraSupport": 3,
        "barOffsetPct": 0,
        "barWidthPct": 72
      },
      {
        "element": "Si",
        "role": "Optional",
        "rangeMin": 0.23,
        "rangeMax": 0.74,
        "spectraSupport": 2,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "Sn",
        "role": "Required",
        "rangeMin": 3.01,
        "rangeMax": 9.52,
        "spectraSupport": 3,
        "barOffsetPct": 10,
        "barWidthPct": 21
      }
    ],
    "ratioGates": [
      {
        "id": "gate-f6a-1",
        "name": "Sn/Cu",
        "numerator": "Sn",
        "denominator": "Cu",
        "min": 0.04,
        "max": 0.16,
        "rationale": "CuSn bronze. Observed 0.106-0.109 on the real bronze particle and 0.10-0.12 on the two seal-ring references. Normalisation-invariant, so it survives the PTFE dilution that makes absolute Cu unreliable.",
        "enabled": true
      }
    ],
    "candidateComponents": [
      {
        "id": "comp-F6a-blade-terminal",
        "name": "Blade Terminal",
        "partNumber": "BOSCH-F6a-BT42",
        "category": "Precision Subcomponent",
        "nominalAlloy": "CuSn8 and similar",
        "confidence": 95,
        "notes": "Observed reference component for F6a (Cu-Sn bronze / Cu-Sn metal matrix composite)."
      },
      {
        "id": "comp-F6a-cri-sealing-ring",
        "name": "CRI Sealing ring",
        "partNumber": "BOSCH-F6a-CSR48",
        "category": "Precision Subcomponent",
        "nominalAlloy": "CuSn8 and similar",
        "confidence": 95,
        "notes": "Observed reference component for F6a (Cu-Sn bronze / Cu-Sn metal matrix composite)."
      }
    ],
    "contextCaveats": [
      {
        "title": "Carbon untracked",
        "description": "C content not reliably determinable via standard EDS.",
        "icon": "warning"
      },
      {
        "title": "Renormalized",
        "description": "Metal-basis renormalized excluding O, C, N, F.",
        "icon": "calculate"
      },
      {
        "title": "Metallurgical note",
        "description": "Sn/Cu is the stable fingerprint; absolute Cu is unreliable because the seal-ring matrix is PTFE-loaded and dilutes every metal reading.",
        "icon": "info"
      }
    ]
  },
  {
    "id": "f6b-cu-sn",
    "code": "F6b",
    "name": "Cu-Sn bronze layer on steel (bimetallic seal ring)",
    "gradeHint": "CuSn overlay on steel backing",
    "status": "PROV",
    "description": "The interaction volume spans a bronze overlay and its steel backing, so BOTH Cu and Fe are matrix-level. Real HP-sealing references sit at Fe 58-64 / Cu 32-36 on the metal basis - between the Cu-rich and steel families, which is why a single-material predicate set missed them entirely. Report as a layered/bimetallic result, not one alloy.",
    "compatibilityScore": 85,
    "totalSpectra": 100,
    "passingSpectra": 98,
    "failingSpectra": 2,
    "elementBands": [
      {
        "element": "Cr",
        "role": "Required",
        "rangeMin": 0.43,
        "rangeMax": 0.86,
        "spectraSupport": 2,
        "barOffsetPct": 1,
        "barWidthPct": 8
      },
      {
        "element": "Cu",
        "role": "Required",
        "rangeMin": 15.67,
        "rangeMax": 52.69,
        "spectraSupport": 2,
        "barOffsetPct": 15,
        "barWidthPct": 37
      },
      {
        "element": "Fe",
        "role": "Required",
        "rangeMin": 57.44,
        "rangeMax": 63.97,
        "spectraSupport": 2,
        "barOffsetPct": 57,
        "barWidthPct": 8
      },
      {
        "element": "Sn",
        "role": "Required",
        "rangeMin": 2.09,
        "rangeMax": 6.85,
        "spectraSupport": 2,
        "barOffsetPct": 6,
        "barWidthPct": 15
      }
    ],
    "ratioGates": [
      {
        "id": "gate-f6b-1",
        "name": "Sn/Cu",
        "numerator": "Sn",
        "denominator": "Cu",
        "min": 0.04,
        "max": 0.16,
        "rationale": "CuSn bronze. Observed 0.106-0.109 on the real bronze particle and 0.10-0.12 on the two seal-ring references. Normalisation-invariant, so it survives the PTFE dilution that makes absolute Cu unreliable.",
        "enabled": true
      }
    ],
    "candidateComponents": [
      {
        "id": "comp-F6b-hp-sealing",
        "name": "HP Sealing",
        "partNumber": "BOSCH-F6b-HS30",
        "category": "Precision Subcomponent",
        "nominalAlloy": "CuSn overlay on steel backing",
        "confidence": 85,
        "notes": "Observed reference component for F6b (Cu-Sn bronze layer on steel (bimetallic seal ring))."
      }
    ],
    "contextCaveats": [
      {
        "title": "Carbon untracked",
        "description": "C content not reliably determinable via standard EDS.",
        "icon": "warning"
      },
      {
        "title": "Renormalized",
        "description": "Metal-basis renormalized excluding O, C, N, F.",
        "icon": "calculate"
      },
      {
        "title": "Metallurgical note",
        "description": "The interaction volume spans a bronze overlay and its steel backing, so BOTH Cu and Fe are matrix-level. Real HP-sealing references sit at Fe 58-64 / Cu 32-36 on the metal basis - between the Cu-rich and steel families, which is why a single-material predicate set missed them entirely. Report as a layered/bimetallic result, not one alloy.",
        "icon": "info"
      }
    ]
  },
  {
    "id": "f7-au-plated",
    "code": "F7",
    "name": "Au-plated electrical contact",
    "gradeHint": "Au plating on Cu/Ni substrate",
    "status": "FIRM",
    "description": "Plating dominates the analysed volume; substrate may be visible beneath.",
    "compatibilityScore": 95,
    "totalSpectra": 100,
    "passingSpectra": 98,
    "failingSpectra": 2,
    "elementBands": [
      {
        "element": "Au",
        "role": "Required",
        "rangeMin": 56.76,
        "rangeMax": 136.71,
        "spectraSupport": 6,
        "barOffsetPct": 56,
        "barWidthPct": 44
      },
      {
        "element": "Cu",
        "role": "Trace",
        "rangeMin": 0.89,
        "rangeMax": 3.31,
        "spectraSupport": 5,
        "barOffsetPct": 2,
        "barWidthPct": 8
      },
      {
        "element": "Ni",
        "role": "Required",
        "rangeMin": 1.31,
        "rangeMax": 2.62,
        "spectraSupport": 6,
        "barOffsetPct": 4,
        "barWidthPct": 8
      }
    ],
    "ratioGates": [],
    "candidateComponents": [
      {
        "id": "comp-F7-blade-terminal",
        "name": "Blade Terminal",
        "partNumber": "BOSCH-F7-BT42",
        "category": "Precision Subcomponent",
        "nominalAlloy": "Au plating on Cu/Ni substrate",
        "confidence": 95,
        "notes": "Observed reference component for F7 (Au-plated electrical contact)."
      },
      {
        "id": "comp-F7-magnet-coil",
        "name": "Magnet Coil",
        "partNumber": "BOSCH-F7-MC33",
        "category": "Precision Subcomponent",
        "nominalAlloy": "Au plating on Cu/Ni substrate",
        "confidence": 95,
        "notes": "Observed reference component for F7 (Au-plated electrical contact)."
      }
    ],
    "contextCaveats": [
      {
        "title": "Carbon untracked",
        "description": "C content not reliably determinable via standard EDS.",
        "icon": "warning"
      },
      {
        "title": "Renormalized",
        "description": "Metal-basis renormalized excluding O, C, N, F.",
        "icon": "calculate"
      },
      {
        "title": "Metallurgical note",
        "description": "Plating dominates the analysed volume; substrate may be visible beneath.",
        "icon": "info"
      }
    ]
  },
  {
    "id": "f8a-zn-coated",
    "code": "F8a",
    "name": "Zn-coated steel (galvanic / electroplated)",
    "gradeHint": "Zn plating on steel",
    "status": "FIRM",
    "description": "A measured coating LAYER, distinct from a coating trace. Fe is deliberately unconstrained: it reads ~72 wt% through a thin layer but under 2 wt% through a thick one, where the substrate is simply not in the interaction volume. Requiring Fe>40 lost every thick-coating spectrum. Substrate grade is NOT determinable here.",
    "compatibilityScore": 95,
    "totalSpectra": 100,
    "passingSpectra": 98,
    "failingSpectra": 2,
    "elementBands": [
      {
        "element": "Cr",
        "role": "Optional",
        "rangeMin": 0.07,
        "rangeMax": 0.94,
        "spectraSupport": 5,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "Fe",
        "role": "Required",
        "rangeMin": 0.31,
        "rangeMax": 72.81,
        "spectraSupport": 6,
        "barOffsetPct": 0,
        "barWidthPct": 72
      },
      {
        "element": "Mn",
        "role": "Optional",
        "rangeMin": 1.16,
        "rangeMax": 2.05,
        "spectraSupport": 1,
        "barOffsetPct": 3,
        "barWidthPct": 8
      },
      {
        "element": "Si",
        "role": "Required",
        "rangeMin": 0.0,
        "rangeMax": 1.96,
        "spectraSupport": 6,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "Zn",
        "role": "Required",
        "rangeMin": 0.0,
        "rangeMax": 133.02,
        "spectraSupport": 6,
        "barOffsetPct": 0,
        "barWidthPct": 100
      }
    ],
    "ratioGates": [],
    "candidateComponents": [
      {
        "id": "comp-F8a-m&m-hpp-component",
        "name": "M&M HPP Component",
        "partNumber": "BOSCH-F8a-MHC51",
        "category": "Precision Subcomponent",
        "nominalAlloy": "Zn plating on steel",
        "confidence": 95,
        "notes": "Observed reference component for F8a (Zn-coated steel (galvanic / electroplated))."
      },
      {
        "id": "comp-F8a-nr-nut",
        "name": "NR Nut",
        "partNumber": "BOSCH-F8a-NN18",
        "category": "Fuel Injector Assembly",
        "nominalAlloy": "Zn plating on steel",
        "confidence": 95,
        "notes": "Observed reference component for F8a (Zn-coated steel (galvanic / electroplated))."
      }
    ],
    "contextCaveats": [
      {
        "title": "Carbon untracked",
        "description": "C content not reliably determinable via standard EDS.",
        "icon": "warning"
      },
      {
        "title": "Renormalized",
        "description": "Metal-basis renormalized excluding O, C, N, F.",
        "icon": "calculate"
      },
      {
        "title": "Metallurgical note",
        "description": "A measured coating LAYER, distinct from a coating trace. Fe is deliberately unconstrained: it reads ~72 wt% through a thin layer but under 2 wt% through a thick one, where the substrate is simply not in the interaction volume. Requiring Fe>40 lost every thick-coating spectrum. Substrate grade is NOT determinable here.",
        "icon": "info"
      }
    ]
  },
  {
    "id": "f8b-zn-phosphate",
    "code": "F8b",
    "name": "Zn-phosphate conversion coating on steel",
    "gradeHint": "Zn phosphating",
    "status": "FIRM",
    "description": "Zn + P together at layer level, with high oxygen in the as-measured spectrum (phosphate anion). Distinguished from F8a by P, and from plain steel by both. Substrate grade is NOT determinable. Zn/P is normalisation-invariant across coating thickness: 1.66-2.71 on 17 of 18 real spectra across 6 components; one measurement (8.32) is excluded as a clear outlier rather than widening the band to cover it.",
    "compatibilityScore": 95,
    "totalSpectra": 228,
    "passingSpectra": 223,
    "failingSpectra": 5,
    "elementBands": [
      {
        "element": "Al",
        "role": "Trace",
        "rangeMin": 0.08,
        "rangeMax": 1.48,
        "spectraSupport": 3,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "Cr",
        "role": "Optional",
        "rangeMin": 0.31,
        "rangeMax": 0.57,
        "spectraSupport": 1,
        "barOffsetPct": 1,
        "barWidthPct": 8
      },
      {
        "element": "Fe",
        "role": "Required",
        "rangeMin": 25.26,
        "rangeMax": 82.59,
        "spectraSupport": 19,
        "barOffsetPct": 25,
        "barWidthPct": 57
      },
      {
        "element": "Mn",
        "role": "Required",
        "rangeMin": 0.41,
        "rangeMax": 3.34,
        "spectraSupport": 19,
        "barOffsetPct": 1,
        "barWidthPct": 9
      },
      {
        "element": "P",
        "role": "Required",
        "rangeMin": 0.01,
        "rangeMax": 27.02,
        "spectraSupport": 19,
        "barOffsetPct": 0,
        "barWidthPct": 90
      },
      {
        "element": "S",
        "role": "Optional",
        "rangeMin": 0.08,
        "rangeMax": 0.28,
        "spectraSupport": 1,
        "barOffsetPct": 0,
        "barWidthPct": 8
      },
      {
        "element": "Si",
        "role": "Optional",
        "rangeMin": 0.04,
        "rangeMax": 2.79,
        "spectraSupport": 14,
        "barOffsetPct": 0,
        "barWidthPct": 9
      },
      {
        "element": "Zn",
        "role": "Required",
        "rangeMin": 0.0,
        "rangeMax": 59.37,
        "spectraSupport": 19,
        "barOffsetPct": 0,
        "barWidthPct": 59
      }
    ],
    "ratioGates": [
      {
        "id": "gate-f8b-1",
        "name": "Zn/P",
        "numerator": "Zn",
        "denominator": "P",
        "min": 1.4,
        "max": 3.0,
        "rationale": "Observed 1.66-2.71 on 17 of 18 real spectra across 6 components; one spectrum (8.32) excluded as an outlier rather than widening the band to cover it. Normalisation-invariant across coating thickness, unlike absolute Zn or P.",
        "enabled": true
      }
    ],
    "candidateComponents": [
      {
        "id": "comp-F8b-ic-stud",
        "name": "IC Stud",
        "partNumber": "BOSCH-F8b-IS21",
        "category": "Precision Subcomponent",
        "nominalAlloy": "Zn phosphating",
        "confidence": 95,
        "notes": "Observed reference component for F8b (Zn-phosphate conversion coating on steel)."
      },
      {
        "id": "comp-F8b-nr-nut",
        "name": "NR Nut",
        "partNumber": "BOSCH-F8b-NN18",
        "category": "Fuel Injector Assembly",
        "nominalAlloy": "Zn phosphating",
        "confidence": 95,
        "notes": "Observed reference component for F8b (Zn-phosphate conversion coating on steel)."
      }
    ],
    "contextCaveats": [
      {
        "title": "Carbon untracked",
        "description": "C content not reliably determinable via standard EDS.",
        "icon": "warning"
      },
      {
        "title": "Renormalized",
        "description": "Metal-basis renormalized excluding O, C, N, F.",
        "icon": "calculate"
      },
      {
        "title": "Metallurgical note",
        "description": "Zn + P together at layer level, with high oxygen in the as-measured spectrum (phosphate anion). Distinguished from F8a by P, and from plain steel by both. Substrate grade is NOT determinable. Zn/P is normalisation-invariant across coating thickness: 1.66-2.71 on 17 of 18 real spectra across 6 components; one measurement (8.32) is excluded as a clear outlier rather than widening the band to cover it.",
        "icon": "info"
      }
    ]
  }
];

export const INITIAL_USERS: UserAccount[] = [
  {
    id: 'user-1',
    name: 'Dr. Marcus Vance',
    email: 'm.vance@spectrallab.io',
    role: 'Snr. Metallurgist',
    department: 'Metallurgy',
    permissions: 'Full Edit',
    avatarUrl: AVATAR_THORNE,
    initials: 'MV',
    isActive: true,
    lastActive: 'Just now',
  },
  {
    id: 'user-2',
    name: 'Sarah Jenkins',
    email: 's.jenkins@spectrallab.io',
    role: 'Lab Tech',
    department: 'Operations',
    permissions: 'Read-only',
    avatarUrl: AVATAR_EYE,
    initials: 'SJ',
    isActive: true,
    lastActive: '12m ago',
  },
  {
    id: 'user-3',
    name: 'Alex Rivera',
    email: 'a.rivera@spectrallab.io',
    role: 'Lab Tech',
    department: 'Operations',
    permissions: 'Read-only',
    avatarUrl: AVATAR_ORB,
    initials: 'AR',
    isActive: true,
    lastActive: '1h ago',
  },
  {
    id: 'user-4',
    name: 'David Chen',
    email: 'd.chen@spectrallab.io',
    role: 'Auditor',
    department: 'Quality Control',
    permissions: 'Read-only',
    initials: 'DC',
    isActive: true,
    lastActive: '3h ago',
  },
  {
    id: 'user-5',
    name: 'Spectrometer ETL Daemon',
    email: 'service-eds@spectrallab.io',
    role: 'Service Acct',
    department: 'System',
    permissions: 'System Execution',
    initials: 'SE',
    isActive: true,
    lastActive: 'Continuous',
  },
];

export const ROLE_DEFINITIONS: RoleDefinition[] = [
  {
    id: 'role-snr-met',
    title: 'Snr. Metallurgist',
    description: 'Full access to modify ratio gates, approve spectral deviations, and edit global Knowledge Base.',
    userCount: 1,
  },
  {
    id: 'role-lab-tech',
    title: 'Lab Tech',
    description: 'Execute scans, log samples, and view historical data. Cannot alter baseline thresholds.',
    userCount: 2,
  },
  {
    id: 'role-auditor',
    title: 'Auditor',
    description: 'Read-only access across all departments. Can export reports and view scan history.',
    userCount: 1,
  },
  {
    id: 'role-service',
    title: 'Service Acct / API',
    description: 'Automated spectrometers and ETL ingest pipelines with programmatic execution rights.',
    userCount: 1,
  },
];

export const INITIAL_AUDIT_LOGS: AuditLogEntry[] = [
  {
    id: 'audit-1',
    timestamp: '2026-09-14 08:30:00',
    user: 'Dr. Marcus Vance',
    userRole: 'Snr. Metallurgist',
    action: 'Calibrated baseline ratio gate Cr/Ni for F4',
    actionType: 'Gate Edit',
    familyCode: 'F4',
    changeDetails: {
      from: 'Cr/Ni: [1.4, 3.2]',
      to: 'Cr/Ni: [1.85, 2.30]',
    },
    impactText: 'Tighter differentiation from 316L and duplex stainless grades',
    impactType: 'positive',
  },
  {
    id: 'audit-2',
    timestamp: '2026-09-14 07:15:22',
    user: 'Spectrometer ETL Daemon',
    userRole: 'Service Acct',
    action: 'Ingested and validated 173 reference spectra from EDS Consolidation',
    actionType: 'Calibration',
    familyCode: 'All',
    changeDetails: {
      from: 'Uncalibrated',
      to: '173 spectra normalised',
    },
    impactText: 'Reference database active',
    impactType: 'positive',
  },
  {
    id: 'audit-3',
    timestamp: '2026-09-13 16:45:10',
    user: 'Sarah Jenkins',
    userRole: 'Lab Tech',
    action: 'Microanalysis scan on Particle In IC Stud (ISUZU)',
    actionType: 'Calibration',
    familyCode: 'F1b',
    changeDetails: {
      from: 'Unknown',
      to: 'F1b (~1.5 Mn plain carbon steel)',
    },
    impactText: 'Guide Bush candidate confirmed',
    impactType: 'neutral',
  },
];
