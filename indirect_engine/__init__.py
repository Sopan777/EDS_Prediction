"""
indirect_engine
===============
Standalone Rule Engine for Probable Indirect Material Source Prediction.
Completely independent from the Direct / Injector Component prediction system.
"""

from indirect_engine.reference_loader import (
    IndirectElementBand,
    IndirectPartReference,
    build_reference_from_excel,
    compute_tolerance_band,
    load_indirect_reference,
)
from indirect_engine.engine import (
    INDIRECT_FAMILY_LABELS,
    IndirectElementCheck,
    IndirectPartCandidate,
    classify_indirect_material_family,
    predict_indirect_particle,
    predict_indirect_source,
    score_indirect_part,
)

__all__ = [
    "INDIRECT_FAMILY_LABELS",
    "IndirectElementBand",
    "IndirectElementCheck",
    "IndirectPartCandidate",
    "IndirectPartReference",
    "build_reference_from_excel",
    "classify_indirect_material_family",
    "compute_tolerance_band",
    "load_indirect_reference",
    "predict_indirect_particle",
    "predict_indirect_source",
    "score_indirect_part",
]
