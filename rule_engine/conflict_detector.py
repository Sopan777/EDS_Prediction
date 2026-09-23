"""
rule_engine/conflict_detector.py
================================
Detects conflicts between declared material metadata and measured EDS composition.

Stdlib only.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ConflictResult:
    has_conflict: bool
    declared_material: Optional[str]
    declared_family: Optional[str]
    measured_family: Optional[str]
    measured_family_id: Optional[str]
    severity: str  # none, warning, critical
    message: str


MATERIAL_FAMILY_MAP = {
    'cusn': ['F6a', 'F6b'],  # CuSn bronze
    'cusn8': ['F6a', 'F6b'],
    'bronze': ['F6a', 'F6b'],
    '100cr6': ['F2'],  # bearing steel
    'sl2 b1': ['F2'],
    'bearing steel': ['F2'],
    'x8crnis': ['F4'],  # austenitic SS
    'x12crnis': ['F4'],
    'aisi 304': ['F4'],
    '304': ['F4'],
    'aisi 316': ['F4'],
    '316': ['F4'],
    'stainless': ['F4'],
    'vdsicr': ['F1c'],  # spring steel
    'din 17223': ['F1c'],
    'spring steel': ['F1c'],
    's6-5-2': ['F3'],  # HSS
    'sl2b17': ['F3'],
    'm2': ['F3'],
    'aisi m2': ['F3'],
    'tool steel': ['F3'],
    '16mncr5': ['F1b'],
}


def detect_conflict(
    declared_material: Optional[str],
    prediction_family_id: Optional[str],
    prediction_family_label: Optional[str],
) -> ConflictResult:
    """
    Detects if the declared material conflicts with the predicted material family.
    
    Args:
        declared_material: The material declared in the metadata (e.g., '100Cr6').
        prediction_family_id: The ID of the family predicted by the engine (e.g., 'F4').
        prediction_family_label: The human-readable label of the predicted family.
        
    Returns:
        ConflictResult detailing if a conflict was found.
    """
    if not declared_material:
        return ConflictResult(
            has_conflict=False,
            declared_material=None,
            declared_family=None,
            measured_family=prediction_family_label,
            measured_family_id=prediction_family_id,
            severity="none",
            message="No declared material to conflict with."
        )

    # Normalize declared material
    norm_declared = declared_material.lower().strip()
    
    # Try to match against MATERIAL_FAMILY_MAP keys
    matched_families = None
    matched_key = None
    
    for key, families in MATERIAL_FAMILY_MAP.items():
        if key in norm_declared:
            matched_families = families
            matched_key = key
            break
            
    if not matched_families:
        return ConflictResult(
            has_conflict=False,
            declared_material=declared_material,
            declared_family=None,
            measured_family=prediction_family_label,
            measured_family_id=prediction_family_id,
            severity="none",
            message=f"Declared material '{declared_material}' is not in the known conflict map."
        )
        
    if not prediction_family_id:
        return ConflictResult(
            has_conflict=False,
            declared_material=declared_material,
            declared_family=f"One of {matched_families}",
            measured_family=prediction_family_label,
            measured_family_id=prediction_family_id,
            severity="none",
            message="No prediction made to compare against."
        )

    if prediction_family_id not in matched_families:
        return ConflictResult(
            has_conflict=True,
            declared_material=declared_material,
            declared_family=str(matched_families),
            measured_family=prediction_family_label,
            measured_family_id=prediction_family_id,
            severity="critical",
            message=f"Conflict: Declared material '{declared_material}' maps to {matched_families}, but measured as {prediction_family_id} ({prediction_family_label})."
        )
        
    return ConflictResult(
        has_conflict=False,
        declared_material=declared_material,
        declared_family=str(matched_families),
        measured_family=prediction_family_label,
        measured_family_id=prediction_family_id,
        severity="none",
        message="Declared material matches measured composition."
    )
