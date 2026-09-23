import pandas as pd
import numpy as np
import json
import re
from pathlib import Path
from datetime import datetime
import sys

# Allow importing rule_engine
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rule_engine.real_data import load_spectra

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ROOT_EXCEL = PROJECT_ROOT / "EDS Consolidation_xlsx(1).xlsx"
MATERIALS_JSON = PROJECT_ROOT / "rule_engine" / "knowledge" / "materials.json"
OUT_FINGERPRINTS = PROJECT_ROOT / "rule_engine" / "knowledge" / "component_fingerprints.json"
OUT_ALIASES = PROJECT_ROOT / "rule_engine" / "knowledge" / "component_aliases.json"

NON_ALLOY_ELEMENTS = {"C", "O", "N", "F", "Ca", "K", "Na", "Cl", "Mg"}
ELEMENT_COLS = ['C', 'O', 'Al', 'Si', 'P', 'S', 'Cr', 'Mn', 'Ni', 'Pb', 'Fe', 'Mo', 'Cu', 'Sn', 'Zn', 'Au', 'K', 'N', 'Ca', 'V', 'W', 'Cl']

def normalize_to_metal_basis(spectrum_values):
    metal_total = sum(v for k, v in spectrum_values.items() if k not in NON_ALLOY_ELEMENTS and v > 0)
    if metal_total == 0:
        return {}
    return {k: (v * 100.0 / metal_total) for k, v in spectrum_values.items() if k not in NON_ALLOY_ELEMENTS and v > 0}

def canonicalize_name(name):
    # E.g., "Armature Bolt" -> "ARMATURE_BOLT"
    return re.sub(r'[^A-Za-z0-9]+', '_', name.strip().upper()).strip('_')

def main():
    # 1. Load root Excel
    df = pd.read_excel(ROOT_EXCEL)
    
    # 2. Load from Excel using rule_engine
    real_spectra = load_spectra()
    
    # Load materials for family mapping
    with open(MATERIALS_JSON, 'r', encoding='utf-8') as f:
        materials_data = json.load(f)
    
    comp_to_families = {}
    for fid, fdata in materials_data.get('families', {}).items():
        for comp in fdata.get('components', []):
            cid = canonicalize_name(comp)
            comp_to_families.setdefault(cid, []).append(fid)
            
    components_data = {}
    total_spectra = 0
    
    # Process root Excel
    for _, row in df.iterrows():
        raw_name = str(row['ComponentName'])
        if raw_name == 'nan' or not raw_name.strip():
            continue
            
        cid = canonicalize_name(raw_name)
        display_name = raw_name.strip()
        mat_body = str(row['Material Body']).strip() if 'Material Body' in row and not pd.isna(row['Material Body']) else None
        
        vals = {}
        for el in ELEMENT_COLS:
            val = row.get(el)
            if not pd.isna(val) and isinstance(val, (int, float)) and val > 0:
                vals[el] = float(val)
                
        norm = normalize_to_metal_basis(vals)
        if cid not in components_data:
            components_data[cid] = {'spectra': [], 'material_bodies': set(), 'display_name': display_name, 'raw_names': set()}
            
        if norm:
            components_data[cid]['spectra'].append(norm)
            total_spectra += 1
            
        if mat_body and mat_body != 'nan':
            components_data[cid]['material_bodies'].add(mat_body)
        components_data[cid]['raw_names'].add(raw_name.strip())
        
    # Process real_spectra
    for sp in real_spectra:
        if not sp.component:
            continue
        raw_name = sp.component
        cid = canonicalize_name(raw_name)
        
        norm = normalize_to_metal_basis(sp.values)
        if cid not in components_data:
            components_data[cid] = {'spectra': [], 'material_bodies': set(), 'display_name': raw_name.strip(), 'raw_names': set()}
            
        if norm:
            components_data[cid]['spectra'].append(norm)
            total_spectra += 1
            
        components_data[cid]['raw_names'].add(raw_name.strip())
        
    # Stats calculation
    out_components = {}
    aliases = {}
    canonical = {}
    
    for cid, data in components_data.items():
        spectra = data['spectra']
        n_spectra = len(spectra)
        if n_spectra == 0:
            continue
            
        mat_bodies = list(data['material_bodies'])
        material_body = mat_bodies[0] if mat_bodies else None
        
        if n_spectra >= 20:
            quality = "HIGH"
        elif n_spectra >= 5:
            quality = "MEDIUM"
        else:
            quality = "LOW"
            
        elements_stats = {}
        all_elements = set()
        for s in spectra:
            all_elements.update(s.keys())
            
        for el in all_elements:
            vals = [s[el] for s in spectra if el in s]
            if not vals:
                continue
                
            scount = len(vals)
            freq = scount / n_spectra
            
            if freq > 0.8:
                role = "expected"
            elif freq >= 0.2:
                role = "common"
            else:
                role = "rare"
                
            q1 = float(np.percentile(vals, 25))
            q3 = float(np.percentile(vals, 75))
            elements_stats[el] = {
                "median": float(np.median(vals)),
                "q1": q1,
                "q3": q3,
                "iqr": float(q3 - q1),
                "mean": float(np.mean(vals)),
                "std": float(np.std(vals)) if scount > 1 else 0.0,
                "min": float(np.min(vals)),
                "max": float(np.max(vals)),
                "sample_count": scount,
                "frequency": freq,
                "role": role
            }
            
        # Ratios
        ratios_to_check = [("Cr", "Fe"), ("Cr", "Ni"), ("Sn", "Cu"), ("Zn", "P"), ("W", "Mo"), ("Mo", "Cr")]
        ratios_stats = {}
        for n, d in ratios_to_check:
            rvals = []
            for s in spectra:
                if n in s and d in s and s[d] > 0:
                    rvals.append(s[n] / s[d])
            if rvals:
                q1 = float(np.percentile(rvals, 25))
                q3 = float(np.percentile(rvals, 75))
                ratio_name = f"{n}/{d}"
                ratios_stats[ratio_name] = {
                    "median": float(np.median(rvals)),
                    "q1": q1,
                    "q3": q3,
                    "sample_count": len(rvals)
                }
                
        fids = sorted(list(set(comp_to_families.get(cid, []))))
        
        # Format output
        for el, stats in elements_stats.items():
            for k, v in stats.items():
                if isinstance(v, float):
                    stats[k] = round(v, 4)
        for r, stats in ratios_stats.items():
            for k, v in stats.items():
                if isinstance(v, float):
                    stats[k] = round(v, 4)
                    
        out_components[cid] = {
            "component_id": cid,
            "display_name": data['display_name'],
            "family_ids": fids,
            "material_body": material_body,
            "sample_count": n_spectra,
            "fingerprint_quality": quality,
            "elements": elements_stats,
            "ratios": ratios_stats
        }
        
        for rn in data['raw_names']:
            aliases[rn] = cid
            aliases[rn.lower()] = cid
            aliases[rn.upper()] = cid
            # Some entries might have weird spacing
            aliases[rn.strip()] = cid
            
        canonical[cid] = {
            "display_name": data['display_name'],
            "family_ids": fids
        }
        
    fingerprints_json = {
        "version": "1.0.0",
        "source": "EDS Consolidation_xlsx(1).xlsx + data/EDS Consolidation.xlsx",
        "total_spectra": total_spectra,
        "total_components": len(out_components),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "components": out_components
    }
    
    aliases_json = {
        "version": "1.0.0",
        "aliases": aliases,
        "canonical": canonical
    }
    
    with open(OUT_FINGERPRINTS, 'w', encoding='utf-8') as f:
        json.dump(fingerprints_json, f, indent=2)
        
    with open(OUT_ALIASES, 'w', encoding='utf-8') as f:
        json.dump(aliases_json, f, indent=2)
        
if __name__ == "__main__":
    main()
