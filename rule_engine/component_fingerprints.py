"""
rule_engine/component_fingerprints.py
=====================================
Runtime loader for component fingerprints. Uses stdlib only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class ElementStats:
    median: float
    q1: float
    q3: float
    iqr: float
    mean: float
    std: float
    min_val: float
    max_val: float
    sample_count: int
    frequency: float
    role: str

@dataclass
class RatioStats:
    median: float
    q1: float
    q3: float
    sample_count: int

@dataclass
class ComponentFingerprint:
    component_id: str
    display_name: str
    family_ids: List[str]
    material_body: Optional[str]
    sample_count: int
    fingerprint_quality: str
    elements: Dict[str, ElementStats]
    ratios: Dict[str, RatioStats]

_CACHE: Optional[Dict[str, ComponentFingerprint]] = None
_ALIASES_CACHE: Optional[Dict[str, str]] = None

def _load_data() -> None:
    global _CACHE, _ALIASES_CACHE
    if _CACHE is not None:
        return
    
    base_dir = Path(__file__).resolve().parent / "knowledge"
    fingerprints_file = base_dir / "component_fingerprints.json"
    aliases_file = base_dir / "component_aliases.json"
    
    if not fingerprints_file.exists() or not aliases_file.exists():
        _CACHE = {}
        _ALIASES_CACHE = {}
        return
        
    with open(fingerprints_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    _CACHE = {}
    for cid, cdata in data.get("components", {}).items():
        elements = {}
        for el, estats in cdata.get("elements", {}).items():
            elements[el] = ElementStats(
                median=float(estats["median"]),
                q1=float(estats["q1"]),
                q3=float(estats["q3"]),
                iqr=float(estats["iqr"]),
                mean=float(estats["mean"]),
                std=float(estats["std"]),
                min_val=float(estats["min"]),
                max_val=float(estats["max"]),
                sample_count=int(estats["sample_count"]),
                frequency=float(estats["frequency"]),
                role=str(estats["role"])
            )
            
        ratios = {}
        for rname, rstats in cdata.get("ratios", {}).items():
            ratios[rname] = RatioStats(
                median=float(rstats["median"]),
                q1=float(rstats["q1"]),
                q3=float(rstats["q3"]),
                sample_count=int(rstats["sample_count"])
            )
            
        _CACHE[cid] = ComponentFingerprint(
            component_id=cdata["component_id"],
            display_name=cdata["display_name"],
            family_ids=cdata.get("family_ids", []),
            material_body=cdata.get("material_body"),
            sample_count=cdata["sample_count"],
            fingerprint_quality=cdata["fingerprint_quality"],
            elements=elements,
            ratios=ratios
        )
        
    with open(aliases_file, "r", encoding="utf-8") as f:
        aliases_data = json.load(f)
    _ALIASES_CACHE = aliases_data.get("aliases", {})

def load_fingerprints() -> Dict[str, ComponentFingerprint]:
    """Returns the loaded component fingerprints cache."""
    _load_data()
    return _CACHE or {}

def resolve_component_name(name: str) -> Optional[str]:
    """Resolves a raw component name to its canonical ID using aliases."""
    if not name:
        return None
    _load_data()
    if _ALIASES_CACHE is None:
        return None
    return _ALIASES_CACHE.get(name) or _ALIASES_CACHE.get(name.strip())

def get_fingerprint(component_name: str) -> Optional[ComponentFingerprint]:
    """Retrieves the fingerprint for a given component name or component ID."""
    if not component_name:
        return None
    _load_data()
    cache = _CACHE or {}
    # 1. Direct ID match
    if component_name in cache:
        return cache[component_name]
    # 2. Case-insensitive ID match
    upper_name = component_name.strip().upper().replace(" ", "_").replace("-", "_")
    if upper_name in cache:
        return cache[upper_name]
    # 3. Alias resolution
    cid = resolve_component_name(component_name)
    if cid and cid in cache:
        return cache[cid]
    # 4. Display name match
    for fp in cache.values():
        if fp.display_name.lower() == component_name.strip().lower():
            return fp
    return None
