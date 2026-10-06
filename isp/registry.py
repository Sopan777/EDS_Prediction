"""Controlled vocabularies, ontologies, and indistinguishability groups (Phase 1, 7, 8, 9, 10)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import re


@dataclass(frozen=True)
class ComponentSpec:
    component_id: str
    canonical_name: str
    pattern: str
    compatible_families: Tuple[str, ...]
    indistinguishability_group: Optional[str] = None
    expected_coatings: Tuple[str, ...] = ()


INTERNAL_COMPONENTS: Tuple[ComponentSpec, ...] = (
    ComponentSpec("IC_STUD", "IC Stud", r"\bic ?stud", ("PLAIN_C_STEEL", "LEADED_PLAIN_C", "MN_CR_MN_STEEL", "BEARING_100CR6"), "BODY_STUD_NHB_VSS_GROUP", ("ZnP", "Zn")),
    ComponentSpec("INJECTOR_BODY", "Injector Body", r"injector body|^body$", ("PLAIN_C_STEEL", "LEADED_PLAIN_C", "MN_CR_MN_STEEL"), "BODY_STUD_NHB_VSS_GROUP", ("ZnP",)),
    ComponentSpec("MAGNET_CORE", "Magnet Core", r"magnet core", ("PURE_IRON_SOFT_MAGNETIC", "PLAIN_C_STEEL"), None, ()),
    ComponentSpec("NHB", "NHB (Nozzle Holder Body)", r"^nhb$", ("PLAIN_C_STEEL", "LEADED_PLAIN_C", "BEARING_100CR6"), "BODY_STUD_NHB_VSS_GROUP", ("ZnP",)),
    ComponentSpec("VSS", "VSS / VSS Screw", r"^vss", ("PLAIN_C_STEEL", "LEADED_PLAIN_C"), "BODY_STUD_NHB_VSS_GROUP", ("ZnP",)),
    ComponentSpec("VALVE_PISTON", "Valve Piston", r"valve piston", ("HSS_TOOL_STEEL",), "HSS_NEEDLE_PISTON_GROUP", ()),
    ComponentSpec("MAGNET_NUT", "Magnet Nut", r"magnet nut", ("FREE_CUTTING_RESULPH_ETG", "MN_CR_MN_STEEL", "PLAIN_C_STEEL"), "NUT_BUSHING_FILTER_GROUP", ("ZnP",)),
    ComponentSpec("NR_NUT", "NR Nut", r"\bnr nut", ("FREE_CUTTING_RESULPH_ETG", "MN_CR_MN_STEEL", "PLAIN_C_STEEL"), "NUT_BUSHING_FILTER_GROUP", ("ZnP",)),
    ComponentSpec("NOZZLE_NEEDLE", "Nozzle Needle", r"nozzle needle|^needle$", ("HSS_TOOL_STEEL",), "HSS_NEEDLE_PISTON_GROUP", ()),
    ComponentSpec("NOZZLE_BODY", "Nozzle Body", r"nozzle body", ("SL48_NOZZLE_STEEL",), None, ()),
    ComponentSpec("INLET_CONNECTOR", "Inlet Connector", r"inlet connector", ("PLAIN_C_STEEL", "LEADED_PLAIN_C"), "BODY_STUD_NHB_VSS_GROUP", ("ZnP",)),
    ComponentSpec("VALVE_BALL", "Valve Ball", r"valve ball", ("CERAMIC_SILICA_CARBO",), None, ()),
    ComponentSpec("SEALING_RING", "Sealing Ring", r"seal(ing)? ring", ("CU_SN_BRONZE", "PLAIN_C_STEEL"), None, ()),
    ComponentSpec("NOZZLE_SPRING", "Nozzle Spring", r"nozzle spring", ("SPRING_CR_SI_STEEL",), "SPRING_STEEL_GROUP", ()),
    ComponentSpec("BUSHING", "Bushing", r"bushing", ("FREE_CUTTING_RESULPH_ETG", "MN_CR_MN_STEEL", "PLAIN_C_STEEL"), "NUT_BUSHING_FILTER_GROUP", ("ZnP",)),
    ComponentSpec("ARMATURE_SPRING", "Armature Spring", r"armature spring", ("SPRING_CR_SI_STEEL",), "SPRING_STEEL_GROUP", ("ZnP",)),
    ComponentSpec("HPP_SLEEVE", "HPP Sleeve", r"hpp sleeve", ("PLAIN_C_STEEL", "ZN_FLAKES_PLATING"), "HPP_SLEEVE_UNION_GROUP", ("Zn",)),
    ComponentSpec("BAR_EDGE_FILTER", "Bar/Edge Filter", r"bar filter|edge filter", ("MN_CR_MN_STEEL", "PLAIN_C_STEEL", "FREE_CUTTING_RESULPH_ETG"), "NUT_BUSHING_FILTER_GROUP", ("ZnP",)),
    ComponentSpec("CLAMPING_SADDLE", "Clamping Saddle", r"clamping saddle", ("NI_ALLOY_PLATING",), None, ("Ni",)),
    ComponentSpec("FIXING_PIN", "Fixing Pin", r"fixing pin", ("SPRING_CR_SI_STEEL",), "SPRING_STEEL_GROUP", ()),
    ComponentSpec("RETAINING_SCREW", "Retaining Screw", r"retaining screw", ("PLAIN_C_STEEL",), "BODY_STUD_NHB_VSS_GROUP", ()),
    ComponentSpec("VALVE_SPRING", "Valve Spring", r"valve spring", ("SPRING_CR_SI_STEEL", "PLAIN_C_STEEL"), "SPRING_STEEL_GROUP", ()),
    ComponentSpec("NOZZLE_NUT", "Nozzle Nut", r"nozzle nut", ("FREE_CUTTING_RESULPH_ETG", "MN_CR_MN_STEEL"), "NUT_BUSHING_FILTER_GROUP", ("ZnP",)),
    ComponentSpec("UNION_NUT", "Union Nut", r"union (external )?nut", ("PLAIN_C_STEEL", "ZN_FLAKES_PLATING"), "HPP_SLEEVE_UNION_GROUP", ("Zn",)),
    ComponentSpec("SHIM", "Shim", r"\bshim\b", ("PLAIN_C_STEEL", "FREE_CUTTING_RESULPH_ETG", "BEARING_100CR6"), "BEARING_100CR6_GROUP", ()),
    ComponentSpec("COPPER_WASHER", "Copper Washer/Shim", r"copper (washer|shim|coupling)", ("CU_SN_BRONZE",), None, ()),
    ComponentSpec("BACK_FLOW_TUBE", "Back Flow Tube", r"back flow tube", ("AUSTENITIC_SS",), "AUSTENITIC_SS_GROUP", ()),
    ComponentSpec("ARMATURE_PLATE", "Armature Plate", r"armature plate", ("BEARING_100CR6",), "BEARING_100CR6_GROUP", ()),
    ComponentSpec("ARMATURE_GUIDE", "Armature Guide", r"armature guide", ("BEARING_100CR6",), "BEARING_100CR6_GROUP", ()),
    ComponentSpec("VALVE_PIECE", "Valve Piece", r"valve piece", ("BEARING_100CR6",), "BEARING_100CR6_GROUP", ()),
    ComponentSpec("MAGNET_SLEEVE", "Magnet Sleeve", r"magnet sleeve", ("AUSTENITIC_SS",), "AUSTENITIC_SS_GROUP", ()),
    ComponentSpec("BA_HEXAFERRITE", "Ba-hexaferrite Magnet", r"barium hexaferrite", ("FERRITE_MAGNET_ALLOY",), None, ()),
    ComponentSpec("VITON_RING", "Viton Ring", r"viton ring", ("CARBON_POLYMER_NONMETAL",), None, ()),
    ComponentSpec("STRAINING_SCREW", "Straining Screw", r"straining screw", ("LEADED_PLAIN_C", "PLAIN_C_STEEL"), "BODY_STUD_NHB_VSS_GROUP", ("ZnP",)),
    ComponentSpec("HPP", "HPP (High Pressure Pipe)", r"^hpp$|probable hpp", ("PLAIN_C_STEEL", "ZN_FLAKES_PLATING"), "HPP_SLEEVE_UNION_GROUP", ("Zn",)),
)

COMPONENT_BY_ID: Dict[str, ComponentSpec] = {c.component_id: c for c in INTERNAL_COMPONENTS}
COMPONENT_BY_NAME: Dict[str, ComponentSpec] = {c.canonical_name.lower(): c for c in INTERNAL_COMPONENTS}

INDISTINGUISHABILITY_GROUPS: Dict[str, Dict[str, object]] = {
    "BODY_STUD_NHB_VSS_GROUP": {
        "label": "Plain / Leaded Carbon Steel Body-Stud-VSS-NHB Group",
        "members": ["IC_STUD", "INJECTOR_BODY", "NHB", "VSS", "INLET_CONNECTOR", "RETAINING_SCREW", "STRAINING_SCREW"],
        "reason": "Shared plain/leaded carbon steel chemistry (Fe ~95-99%, Mn ~0.7-1.0%) and Zn-phosphate surface treatment.",
    },
    "HSS_NEEDLE_PISTON_GROUP": {
        "label": "HSS Tool Steel (Sl2b17 / Sl4b2 / S6-5-2) Needle-Piston Group",
        "members": ["NOZZLE_NEEDLE", "VALVE_PISTON"],
        "reason": "Both fabricated from high-speed tool steel (Sl2b17 / M2); co-occur in 19/20 report records.",
    },
    "SPRING_STEEL_GROUP": {
        "label": "Si-Cr Spring Steel (VDSiCrDIN) Group",
        "members": ["ARMATURE_SPRING", "NOZZLE_SPRING", "VALVE_SPRING", "FIXING_PIN"],
        "reason": "Shared Si-Cr spring steel chemistry (Si ~1.3-1.9%, Cr ~0.6-0.8%, Mn ~0.6%).",
    },
    "NUT_BUSHING_FILTER_GROUP": {
        "label": "Free-Cutting / Mn-Steel Nut-Bushing-Filter Group",
        "members": ["MAGNET_NUT", "NR_NUT", "BUSHING", "BAR_EDGE_FILTER", "NOZZLE_NUT"],
        "reason": "Shared ETG100 / 1.2-1.5 Mn / resulphurised steel grades (Mn ~1.0-1.5%, Fe balance).",
    },
    "BEARING_100CR6_GROUP": {
        "label": "100Cr6 Bearing Steel Group",
        "members": ["ARMATURE_PLATE", "ARMATURE_GUIDE", "VALVE_PIECE", "SHIM"],
        "reason": "Shared 100Cr6 (Sl2 B1) bearing steel chemistry (Cr ~1.4-1.8%, Si ~0.3%, Mn ~0.3%).",
    },
    "HPP_SLEEVE_UNION_GROUP": {
        "label": "HPP / Sleeve / Union Nut Group",
        "members": ["HPP", "HPP_SLEEVE", "UNION_NUT"],
        "reason": "Shared plain carbon steel tube/nut stock with Zn electroplating.",
    },
    "AUSTENITIC_SS_GROUP": {
        "label": "Austenitic Stainless Steel (SS 302/304) Group",
        "members": ["BACK_FLOW_TUBE", "MAGNET_SLEEVE"],
        "reason": "Shared 18Cr-8Ni austenitic stainless steel grade.",
    },
}

EXTERNAL_PATTERN = re.compile(
    r"jig|fixture|tank|table|tools?\b|tissue|cotton|duster|paper|paint|grinding|corrugated|stationary|"
    r"cloth|thread|plastic|dirt|dust|muck|lint|polymer|nylon|pipes?\b|probable external|general purpose|"
    r"vci|wires|flake from|epoxy|filters\b|oily|shot blasting|protection cap|cellulose|as in table|as per table|refer",
    re.IGNORECASE,
)

PLACEHOLDER_PATTERN = re.compile(r"^[\W_‘’“”\-\?]*$|^200$")


def normalize_token(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip().lower())


def is_garbage_text(t: str) -> bool:
    if not t:
        return False
    s = str(t)
    nonascii = sum(1 for c in s if ord(c) > 127 or c in "$\\")
    return nonascii >= 2 or len(s) > 70 or "rtv" in s.lower() or "ojqj" in s.lower()


def classify_source_token(raw_token: str) -> Tuple[str, Optional[str]]:
    """Return (token_class, canonical_component_id_or_None)."""
    n = normalize_token(raw_token)
    if not n:
        return ("UNRESOLVED", None)
    if is_garbage_text(n):
        return ("GARBAGE", None)
    for spec in INTERNAL_COMPONENTS:
        if re.search(spec.pattern, n):
            return ("INTERNAL", spec.component_id)
    if EXTERNAL_PATTERN.search(n):
        return ("EXTERNAL", None)
    return ("UNRESOLVED", None)


def parse_candidate_list(raw_field: Optional[str]) -> Tuple[List[str], List[Dict[str, object]], str]:
    """Parse a raw source string into (internal_component_ids, token_records, scope)."""
    if not raw_field or (isinstance(raw_field, float)):
        return [], [], "UNRESOLVED"
    tokens = [t for t in re.split(r"[;,]", str(raw_field)) if t.strip()]
    internal: List[str] = []
    records: List[Dict[str, object]] = []
    classes: List[str] = []
    for pos, tok in enumerate(tokens):
        cls, cid = classify_source_token(tok)
        classes.append(cls)
        records.append({"position": pos, "raw_token": tok.strip()[:120], "cls": cls, "component_id": cid})
        if cid and cid not in internal:
            internal.append(cid)
    if internal and "EXTERNAL" not in classes:
        scope = "INTERNAL_ONLY"
    elif internal:
        scope = "MIXED"
    elif "EXTERNAL" in classes:
        scope = "EXTERNAL_ONLY"
    else:
        scope = "UNRESOLVED"
    return internal, records, scope


# --- Material Family Ontology (14 canonical families) ---
MATERIAL_FAMILIES: Dict[str, str] = {
    "PURE_IRON_SOFT_MAGNETIC": "Soft Magnetic Pure Iron",
    "PLAIN_C_STEEL": "Plain Carbon / Low-Alloy Steel",
    "LEADED_PLAIN_C": "Leaded Plain Carbon Steel",
    "MN_CR_MN_STEEL": "Mn / Cr-Mn Steel (1.2-1.5 Mn)",
    "FREE_CUTTING_RESULPH_ETG": "Resulphurised / ETG100 Steel",
    "BEARING_100CR6": "100Cr6 Bearing Steel (Sl2 B1)",
    "SPRING_CR_SI_STEEL": "Si-Cr Spring Steel (VDSiCrDIN)",
    "HSS_TOOL_STEEL": "High-Speed Tool Steel (Sl2b17 / Sl4b2 / M2)",
    "SL48_NOZZLE_STEEL": "Sl48 Case-Hardening Nozzle Steel",
    "AUSTENITIC_SS": "Stainless Steel (SS 302/304/316)",
    "CU_SN_BRONZE": "Cu / Cu-Sn Bronze / Brass",
    "NI_ALLOY_PLATING": "Nickel Alloy / Ni Plating",
    "ZN_FLAKES_PLATING": "Zinc Flake / Zn Phosphate / Zn Plating",
    "CERAMIC_SILICA_CARBO": "Ceramic / Al-Si / Silica-Carbo",
    "FERRITE_MAGNET_ALLOY": "Magnetic Ceramic / Sm-Co / Ferrite",
    "CARBON_POLYMER_NONMETAL": "Carbon Base / Polymer / Non-Metallic",
}


def map_chemistry_to_family(chemistry_raw: Optional[str]) -> Optional[str]:
    """Map analyst chemistry text to canonical family ID (None if garbage/missing)."""
    if not chemistry_raw or not isinstance(chemistry_raw, str):
        return None
    if is_garbage_text(chemistry_raw):
        return None
    s = chemistry_raw.strip().lower()
    if not s or PLACEHOLDER_PATTERN.match(s):
        return None
    if re.search(r"leaded|^pb |lead ", s):
        return "LEADED_PLAIN_C"
    if re.search(r"resulph|etg ?100", s):
        return "FREE_CUTTING_RESULPH_ETG"
    if re.search(r"100cr6", s):
        return "BEARING_100CR6"
    if re.search(r"sl2b17|hss|tool steel|high speed|sl4b2", s):
        return "HSS_TOOL_STEEL"
    if re.search(r"sl ?48", s):
        return "SL48_NOZZLE_STEEL"
    if re.search(r"spring|vdsicr|cr-si", s):
        return "SPRING_CR_SI_STEEL"
    if re.search(r"ss ?3|ss ?4|stainless|cr ni", s):
        return "AUSTENITIC_SS"
    if re.search(r"cu|brass", s):
        return "CU_SN_BRONZE"
    if re.search(r"nickel|ni plat|^nil base", s):
        return "NI_ALLOY_PLATING"
    if re.search(r"mn steel|cr- ?mn|zinc- mn", s):
        return "MN_CR_MN_STEEL"
    if re.search(r"zn|zinc", s):
        return "ZN_FLAKES_PLATING"
    if re.search(r"silica.*carbo|al-si|al alloy|aluminum|alumina|refractory|al oxide", s):
        return "CERAMIC_SILICA_CARBO"
    if re.search(r"sm-co|srfe|barium|ferrite", s):
        return "FERRITE_MAGNET_ALLOY"
    if re.search(r"^iron$|^iron base", s):
        return "PURE_IRON_SOFT_MAGNETIC"
    if re.search(r"plain|palin|low alloy|diffused", s):
        return "PLAIN_C_STEEL"
    if re.search(r"carbon|non ?metallic|polymer|thread|vaseline|poly|^non$", s):
        return "CARBON_POLYMER_NONMETAL"
    return None


# --- Surface / Coating Ontology ---
def normalize_coating(raw_val: Optional[str]) -> Tuple[str, Optional[str], str]:
    """Return (coating_state, coating_type, basis).
    coating_state in {COATED, NONE, TRACES, UNKNOWN}.
    """
    if raw_val is None or (isinstance(raw_val, float)):
        return ("UNKNOWN", None, "missing")
    s = str(raw_val).strip().lower()
    if not s:
        return ("UNKNOWN", None, "missing")
    if s == "nil":
        return ("NONE", None, "explicit_nil")
    if PLACEHOLDER_PATTERN.match(s) or "--" in s or "??" in s:
        return ("UNKNOWN", None, "placeholder")
    typ = (
        "ZnP" if re.search(r"znp|phosphat", s)
        else "Zn" if re.search(r"\bzn|zinc", s)
        else "Ni" if re.search(r"\bni\b|nickel|ni plat", s)
        else None
    )
    if "trace" in s:
        return ("TRACES", typ, "traces")
    if typ:
        return ("COATED", typ, "explicit")
    return ("UNKNOWN", None, "unrecognised")


# --- Particle Location Ontology ---
LOCATION_ZONES: Tuple[Tuple[str, str], ...] = (
    ("IC_STUD_INLET", r"ic ?stud"),
    ("BODY_Z_HOLE_VALVE", r"z hole|valve piece|ball guide|dia 2\.2|body"),
    ("NOZZLE_SEAT_SPRAY", r"nb seat|needle seat|nozzle|spray hole|small o[- ]?ring|cu washer"),
    ("FILTER_BFT", r"bar.?filter|b/f|bft|\bfilter"),
    ("ARMATURE_GROUP", r"armature|ah\.? plate|ah group|vfk|ah\.? bolt"),
    ("MAGNET_GROUP", r"magnet"),
    ("VALVE_PISTON_AREA", r"piston|vss"),
)


def map_location_zone(location_raw: Optional[str], candidate_ids: Optional[List[str]] = None) -> Tuple[str, bool]:
    """Return (location_zone, has_candidate_name_leak)."""
    if not location_raw or not isinstance(location_raw, str):
        return ("UNKNOWN_ZONE", False)
    s = normalize_token(location_raw)
    if not s:
        return ("UNKNOWN_ZONE", False)
    leak = False
    if candidate_ids:
        for cid in candidate_ids:
            spec = COMPONENT_BY_ID.get(cid)
            if spec and re.search(spec.pattern, s):
                leak = True
                break
    for zone, pat in LOCATION_ZONES:
        if re.search(pat, s):
            return (zone, leak)
    return ("OTHER_ZONE", leak)
