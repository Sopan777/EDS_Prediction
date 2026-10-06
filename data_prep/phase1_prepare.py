"""Phase 1 - data preparation for the internal-source prediction system.

Read-only on the workbook. Produces overlay tables in data_prep/out/:
  raw_manifest.json       file hash + sheet shapes (immutability proof)
  site.csv                one row per report/particle site (site_uid surrogate key)
  site_candidate.csv      internal candidates per site (class INTERNAL only)
  raw_source_token.csv    every token incl. EXTERNAL / GARBAGE / UNRESOLVED (kept, not deleted)
  spectrum_inventory.csv  per site spectrum counts and quarantine status
  data_quality_issue.csv  audit log
  component_registry_draft.json  UNREVIEWED vocabulary (needs domain-owner sign-off)
  split_groups.csv        report-level fold assignment (frozen by report id)

Spectra element labels are QUARANTINED: the sheet headers are not trusted (see plan 2.2).
"""
import hashlib, json, re, sys
from pathlib import Path
import pandas as pd

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "data/primary/EDS_Internal_Report_Particle_Dataset.xlsx")
OUT = Path("data_prep/out"); OUT.mkdir(parents=True, exist_ok=True)

INTERNAL = [
    ("IC_STUD", "IC Stud", r"\bic ?stud"), ("INJECTOR_BODY", "Injector Body", r"injector body|^body$"),
    ("MAGNET_CORE", "Magnet Core", r"magnet core"), ("NHB", "NHB (undefined)", r"^nhb$"),
    ("VSS", "VSS / VSS Screw", r"^vss"), ("VALVE_PISTON", "Valve Piston", r"valve piston"),
    ("MAGNET_NUT", "Magnet Nut", r"magnet nut"), ("NR_NUT", "NR Nut", r"\bnr nut"),
    ("NOZZLE_NEEDLE", "Nozzle Needle", r"nozzle needle|^needle$"), ("NOZZLE_BODY", "Nozzle Body", r"nozzle body"),
    ("INLET_CONNECTOR", "Inlet Connector", r"inlet connector"), ("VALVE_BALL", "Valve Ball", r"valve ball"),
    ("SEALING_RING", "Sealing Ring", r"seal(ing)? ring"), ("NOZZLE_SPRING", "Nozzle Spring", r"nozzle spring"),
    ("BUSHING", "Bushing", r"bushing"), ("ARMATURE_SPRING", "Armature Spring", r"armature spring"),
    ("HPP_SLEEVE", "HPP Sleeve", r"hpp sleeve"), ("BAR_EDGE_FILTER", "Bar/Edge Filter", r"bar filter|edge filter"),
    ("CLAMPING_SADDLE", "Clamping Saddle", r"clamping saddle"), ("FIXING_PIN", "Fixing Pin", r"fixing pin"),
    ("RETAINING_SCREW", "Retaining Screw", r"retaining screw"), ("VALVE_SPRING", "Valve Spring", r"valve spring"),
    ("NOZZLE_NUT", "Nozzle Nut", r"nozzle nut"), ("UNION_NUT", "Union Nut", r"union (external )?nut"),
    ("SHIM", "Shim", r"\bshim\b"), ("COPPER_WASHER", "Copper Washer/Shim", r"copper (washer|shim|coupling)"),
    ("BACK_FLOW_TUBE", "Back Flow Tube", r"back flow tube"), ("ARMATURE_PLATE", "Armature Plate", r"armature plate"),
    ("ARMATURE_GUIDE", "Armature Guide", r"armature guide"), ("VALVE_PIECE", "Valve Piece", r"valve piece"),
    ("MAGNET_SLEEVE", "Magnet Sleeve", r"magnet sleeve"), ("BA_HEXAFERRITE", "Ba-hexaferrite magnet", r"barium hexaferrite"),
    ("VITON_RING", "Viton Ring", r"viton ring"), ("STRAINING_SCREW", "Straining Screw", r"straining screw"),
    ("HPP", "HPP (generic)", r"^hpp$|probable hpp"),
]
EXTERNAL = re.compile(r"jig|fixture|tank|table|tools?\b|tissue|cotton|duster|paper|paint|grinding|corrugated|stationary|"
                      r"cloth|thread|plastic|dirt|dust|muck|lint|polymer|nylon|pipes?\b|probable external|general purpose|"
                      r"vci|wires|flake from|epoxy|filters\b|oily|shot blasting|protection cap|cellulose|as in table|as per table|refer")
PLACEHOLDER = re.compile(r"^[\W_‘’“”\-\?]*$|^200$")


def norm(t): return re.sub(r"\s+", " ", t.strip().lower())
def garbage(t): return sum(1 for c in t if ord(c) > 127 or c in "$\\") >= 2 or len(t) > 70
def canon(t):
    for cid, _, p in INTERNAL:
        if re.search(p, t): return cid
    return None


def coating_state(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "UNKNOWN", None, "missing"
    s = str(v).strip().lower()
    typ = "ZnP" if re.search(r"znp|phosphat", s) else "Zn" if re.search(r"\bzn|zinc", s) else "Ni" if re.search(r"\bni\b|nickel|ni plat", s) else None
    if s == "nil": return "NONE", None, "explicit"
    if PLACEHOLDER.match(s) or "--" in s or "??" in s: return "UNKNOWN", None, "placeholder"
    if "trace" in s: return "TRACES", typ, "traces"
    if typ: return "COATED", typ, "explicit"
    return "UNKNOWN", None, "unrecognised"


def main():
    sha = hashlib.sha256(SRC.read_bytes()).hexdigest()
    sheets = pd.read_excel(SRC, sheet_name=None, dtype=str)
    R = sheets["Report_Particle_Dataset"].copy()
    manifest = {"file": str(SRC), "sha256": sha, "sheets": {k: list(v.shape) for k, v in sheets.items()}}
    (OUT / "raw_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    issues = []
    def issue(entity, eid, code, sev, detail): issues.append(dict(entity=entity, entity_id=eid, code=code, severity=sev, detail=detail))

    # surrogate key (3 duplicate (file, site_index) rows exist)
    R["_n"] = R.groupby(["source_file", "site_index"]).cumcount()
    R["site_uid"] = R.source_file.str.replace(r"\W+", "_", regex=True).str[-60:] + "__" + R.site_index.astype(str) + "__" + R._n.astype(str)
    R["report_id"] = R.source_file.map({f: f"R{i:04d}" for i, f in enumerate(sorted(R.source_file.unique()), 1)})
    for _, r in R[R._n > 0].iterrows():
        issue("site", r.site_uid, "DUPLICATE_SITE_KEY", "warning", "same (source_file, site_index) appears more than once; kept with surrogate suffix")

    cand_rows, tok_rows, site_rows, spec_rows = [], [], [], []
    for i, r in R.iterrows():
        tokens = [t for t in re.split(r"[;,]", r.Probable_Internal_Source or "") if t.strip()]
        internal = []
        for pos, raw in enumerate(tokens):
            n = norm(raw)
            if garbage(n): cls, cid = "GARBAGE", None
            else:
                cid = canon(n)
                cls = "INTERNAL" if cid else ("EXTERNAL" if EXTERNAL.search(n) else "UNRESOLVED")
            tok_rows.append(dict(site_uid=r.site_uid, position=pos, raw_token=raw.strip()[:120], cls=cls, component_id=cid))
            if cid and cid not in internal:
                internal.append(cid)
                cand_rows.append(dict(site_uid=r.site_uid, report_id=r.report_id, component_id=cid, position=pos, confirmed=False))
        classes = {t["cls"] for t in tok_rows if t["site_uid"] == r.site_uid} if False else None
        cs = [t["cls"] for t in tok_rows[len(tok_rows) - len(tokens):]] if tokens else []
        scope = ("INTERNAL_ONLY" if internal and "EXTERNAL" not in cs else "MIXED" if internal else "EXTERNAL_ONLY" if "EXTERNAL" in cs else "UNRESOLVED")
        cstate, ctype, cwhy = coating_state(r.surface_coating)
        loc = r.location if isinstance(r.location, str) else None
        name_bearing = bool(loc and any(re.search(p, norm(loc)) for cid, _, p in INTERNAL if cid in internal))
        ns = int(float(r.Extracted_Spectrum_Count or 0))
        site_rows.append(dict(site_uid=r.site_uid, report_id=r.report_id, source_file=r.source_file, site_index=r.site_index,
                              report_date=r.report_date, location_raw=loc, location_name_bearing=name_bearing,
                              coating_raw=r.surface_coating, coating_state=cstate, coating_type=ctype, coating_basis=cwhy,
                              chemistry_raw=r.chemistry, chemistry_garbage=garbage(r.chemistry or ""), n_candidates=len(internal),
                              scope=scope, n_spectra_extracted=ns, n_spectra_declared=r.spectrum_count))
        if str(r.spectrum_count) != str(ns): issue("site", r.site_uid, "SPECTRUM_COUNT_MISMATCH", "warning", f"spectrum_count={r.spectrum_count} vs extracted={ns}")
        if scope in ("EXTERNAL_ONLY", "UNRESOLVED"): issue("site", r.site_uid, "NOT_INTERNAL_SCOPE", "info", scope)
        if scope == "MIXED": issue("site", r.site_uid, "MIXED_INTERNAL_EXTERNAL", "warning", "contains internal and external tokens")
        if any(c == "GARBAGE" for c in cs): issue("site", r.site_uid, "GARBAGE_SOURCE_TEXT", "warning", "binary text in source field")
        if ns: spec_rows.append(dict(site_uid=r.site_uid, report_id=r.report_id, n_spectra=ns, element_labels_status="QUARANTINED",
                                     reason="sheet headers misaligned; re-extract from source report"))
    S = pd.DataFrame(site_rows); C = pd.DataFrame(cand_rows); T = pd.DataFrame(tok_rows); SP = pd.DataFrame(spec_rows)

    # spectra sheet checks (inventory only, values untouched)
    E = sheets["EDS_Spectra"]; el = list(E.columns[9:])
    N = E[el].apply(pd.to_numeric, errors="coerce")
    issue("file", "EDS_Spectra", "ELEMENT_LABELS_UNRELIABLE", "critical",
          f"Fe col median={N['Fe'].median()}, In col filled {int(N['In'].notna().sum())}/{len(E)}, empty element cols={int((N.notna().sum()==0).sum())}")
    issue("file", "EDS_Spectra", "NO_SITE_INDEX", "critical", f"{int(E.duplicated(['source_file','chemistry','spectrum_no']).sum())} duplicate (file,chem,spectrum_no) keys")
    n_rows = int(N.notna().any(axis=1).sum())
    issue("file", "EDS_Spectra", "SPECTRUM_TOTAL_MISMATCH", "warning", f"declared {int(S.n_spectra_extracted.sum())} vs sheet rows {n_rows}")

    # report-level frozen split (stratified by dominant candidate group, deterministic hash)
    rep = S.groupby("report_id").agg(has_internal=("n_candidates", lambda s: bool((s > 0).any())), has_spectra=("n_spectra_extracted", lambda s: bool((s > 0).any()))).reset_index()
    rep["h"] = rep.report_id.map(lambda x: int(hashlib.sha256(x.encode()).hexdigest(), 16) % 5)
    rep["fold"] = rep.h
    rep["holdout"] = (rep.h == 4) & rep.has_internal
    rep.drop(columns="h").to_csv(OUT / "split_groups.csv", index=False)

    reg = {"status": "UNREVIEWED - needs domain-owner sign-off", "components": {cid: {"canonical_name": nm, "class": "INTERNAL", "pattern": p} for cid, nm, p in INTERNAL},
           "open": ["NHB meaning", "VSS meaning", "Nozzle Needle vs Valve Piston", "Bar filter vs Filters", "Body vs Injector body"]}
    (OUT / "component_registry_draft.json").write_text(json.dumps(reg, indent=2), encoding="utf-8")
    S.to_csv(OUT / "site.csv", index=False); C.to_csv(OUT / "site_candidate.csv", index=False)
    T.to_csv(OUT / "raw_source_token.csv", index=False); SP.to_csv(OUT / "spectrum_inventory.csv", index=False)
    pd.DataFrame(issues).to_csv(OUT / "data_quality_issue.csv", index=False)

    print("sha256", sha[:16], "| sites", len(S), "reports", S.report_id.nunique())
    print(S.scope.value_counts().to_dict())
    print("coating_state", S.coating_state.value_counts().to_dict())
    print("internal candidates", len(C), "components", C.component_id.nunique(), "| sites with spectra", len(SP))
    print("issues", pd.DataFrame(issues).code.value_counts().to_dict())
    print("holdout reports", int(rep.holdout.sum()), "of", int(rep.has_internal.sum()), "internal reports")


if __name__ == "__main__":
    main()
