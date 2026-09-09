"""
app_rule.py
===========
Terminal application for EDS material-family identification using the
deterministic compatibility engine in rule_engine/scoring.py.

This tool accepts element composition values (weight percentages) and
identifies the most likely material family - not a single component name.
See docs/EDS_AUDIT.md section 9 for why: on real component centroids with
concentration-dependent measurement uncertainty, colliding pairs stay
entirely within one material family at every noise level tested, so exact
component identity is not recoverable from EDS composition alone. A
"forbidden but never verified as correct" ANSWER is worse than an honest
"insufficient evidence, could be any of these N components" - abstention and
ambiguous sets are first-class answers here, not failure modes.

This previously called rule_engine.engine.RuleEngine, a pure conjunctive AND
filter over rule_engine/rules/rules.json with a confidence value frozen at
training time. That engine returned confident wrong answers: {S: 0.2}
matched "Guide Bush" at confidence 1.00 despite Guide Bush's every reference
spectrum carrying 1.12-1.60 wt% Mn. See docs/EDS_AUDIT.md for the full audit.

Usage:

    # Interactive mode - follow prompts
    python app_rule.py

    # Single identification from command line
    python app_rule.py --predict "Cr=17.5,Ni=8.5,Mn=1.5,Si=0.4"

    # Batch identification from a JSON file
    python app_rule.py --batch spectra.json

    # Show all known material families
    python app_rule.py --list-families

    # Show the family/component detail for one family
    python app_rule.py --family-info F1b

This is a terminal-only tool (no web UI). It requires rule_engine/ in the
same folder.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from rule_engine.scoring import (
        Decision,
        FamilyScore,
        KnowledgeBase,
        Prediction,
        get_knowledge_base,
        predict_particle,
        predict_spectrum,
    )
except ImportError as e:
    print(f"ERROR: Could not import rule_engine.scoring: {e}")
    print("Make sure rule_engine/ is in the same folder as app_rule.py, and that")
    print("rule_engine/knowledge/{sigma_model,materials}.json have been generated:")
    print("    python training/derive_sigma_model.py")
    print("    python training/derive_knowledge.py")
    sys.exit(1)


# --------------------------------------------------------------------------
# Terminal colors (optional - degrades gracefully)
# --------------------------------------------------------------------------

try:
    import colorama
    colorama.init()
    _C = {
        "green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m",
        "cyan": "\033[96m", "bold": "\033[1m", "dim": "\033[2m", "reset": "\033[0m",
    }
except Exception:
    _C = {k: "" for k in ("green", "red", "yellow", "cyan", "bold", "dim", "reset")}


def c(text: str, colour: str) -> str:
    """Apply terminal color to text."""
    return f"{_C[colour]}{text}{_C['reset']}"


# --------------------------------------------------------------------------
# Banner
# --------------------------------------------------------------------------

BANNER = r"""
 ███████╗██████╗ ███████╗    ██████╗ ██╗   ██╗██╗     ███████╗███████╗
 ██╔════╝██╔══██╗██╔════╝    ██╔══██╗██║   ██║██║     ██╔════╝██╔════╝
 █████╗  ██║  ██║███████╗    ██████╔╝██║   ██║██║     █████╗  ███████╗
 ██╔══╝  ██║  ██║╚════██║    ██╔═══╝ ██║   ██║██║     ██╔══╝  ╚════██║
 ███████╗██████╔╝███████║    ██║     ╚██████╔╝███████╗███████╗███████║
 ╚══════╝╚═════╝ ╚══════╝    ╚═╝      ╚═════╝ ╚══════╝╚══════╝╚══════╝
"""


def print_banner():
    """Print the application banner."""
    print(c(BANNER, "cyan"))
    print(c("  Material-Family Identification Engine", "bold"))
    print(c("  Deterministic compatibility scoring over a metal-normalised basis.", "dim"))
    print()


# --------------------------------------------------------------------------
# Terminal table rendering
# --------------------------------------------------------------------------

def _visible_len(s: str) -> int:
    """Calculate visible length of a string (ignoring ANSI color codes)."""
    plain = s
    for code in _C.values():
        if code:
            plain = plain.replace(code, "")
    return len(plain)


def print_table(headers: List[str], rows: List[List[str]]):
    """Print a formatted terminal table with borders."""
    widths = [len(h) for h in headers]
    str_rows = []
    for row in rows:
        str_row = [str(cell) for cell in row]
        str_rows.append(str_row)
        for i, cell in enumerate(str_row):
            if i < len(widths):
                widths[i] = max(widths[i], _visible_len(cell))

    def sep(left, mid, right):
        return left + mid.join("─" * (w + 2) for w in widths) + right

    def row_line(cells):
        parts = []
        for cell, w in zip(cells, widths):
            pad = w - _visible_len(cell)
            parts.append(" " + cell + " " * (pad + 1))
        return "│" + "│".join(parts) + "│"

    print(sep("┌", "┬", "┐"))
    print(row_line([c(h, "cyan") for h in headers]))
    print(sep("├", "┼", "┤"))
    for str_row in str_rows:
        print(row_line(str_row))
    print(sep("└", "┴", "┘"))


# --------------------------------------------------------------------------
# Parsing helpers
# --------------------------------------------------------------------------

def parse_element_string(element_str: str) -> Dict[str, Any]:
    """
    Parse element values from a comma-separated string.

    Format: "Cr=17.5,Ni=8.5,Mn=1.5" or "Cr:17.5,Ni:8.5,Mn:1.5"

    A value of "-" or blank means "analysed, not detected" - this parses it
    to that placeholder string rather than 0.0, so normalize_spectrum can
    tell it apart from a genuine measured zero. See docs/EDS_AUDIT.md root
    cause RC1: collapsing that distinction to 0.0 is why "{S: 0.2}" used to
    match "Guide Bush" - the absent Mn satisfied a >=0 lower bound that
    should have excluded it.
    """
    values: Dict[str, Any] = {}
    parts = element_str.strip().split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            key, val = part.split("=", 1)
        elif ":" in part:
            key, val = part.split(":", 1)
        else:
            print(c(f"  WARNING: Skipping invalid part '{part}' (use Element=Value format)", "yellow"))
            continue
        key = key.strip()
        val = val.strip()
        if val in ("-", "", "n/a", "N/A", "nil", "."):
            values[key] = None  # analysed, not detected
            continue
        try:
            values[key] = float(val)
        except ValueError:
            print(c(f"  WARNING: Non-numeric value for '{key}': '{val}' - treated as not detected", "yellow"))
            values[key] = None
    return values


def load_batch_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Load a batch of spectra from a JSON file.

    Expected format: list of dicts, each dict mapping element names to values.
    Example: [{"Cr": 17.5, "Ni": 8.5}, {"Cu": 45.0, "Sn": 5.0}]

    Also supports labeled format:
    [{"label": "Sample 1", "values": {"Cr": 17.5, "Ni": 8.5}}, ...]
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Batch file not found: {file_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Batch file must contain a JSON array of element dicts")

    spectra = []
    for item in data:
        if isinstance(item, dict):
            if "values" in item:
                spectra.append(item)
            else:
                spectra.append({"values": item})
        else:
            raise ValueError(f"Each item in the batch must be a dict, got: {type(item).__name__}")

    return spectra


# --------------------------------------------------------------------------
# Prediction display
# --------------------------------------------------------------------------

def format_decision(decision: str) -> str:
    """Format a decision with color."""
    if decision == "identified":
        return c(decision, "green")
    if decision == "ambiguous":
        return c(decision, "yellow")
    if decision == "unknown":
        return c(decision, "red")
    return decision


def display_prediction(result: Prediction, label: str = ""):
    """Display a single prediction result in a readable format."""
    if label:
        print(f"\n  {c(label, 'bold')}")
        print(c("  " + "-" * 50, "dim"))

    print(f"  {c('Decision:', 'bold')}     {format_decision(result.decision.value)}")

    if result.top is not None:
        print(f"  {c('Family:', 'bold')}       {result.top.label}")
        if result.top.grade_hint:
            print(f"  {c('Grade hint:', 'bold')}   {result.top.grade_hint}")
        print(f"  {c('Compatibility:', 'bold')} {result.top.compatibility:.2%}")
        print(f"  {c('Margin:', 'bold')}       {result.margin:.3f}")
    else:
        print(f"  {c('Reason:', 'bold')}       {result.reason}")

    if len(result.families) > 1 and result.decision.value == "ambiguous":
        print(f"\n  {c('Ambiguous between:', 'bold')}")
        for fam in result.families:
            print(f"    - {fam.label}  (compatibility {fam.compatibility:.2%})")

    candidates = result.candidate_components
    if candidates:
        print(f"\n  {c('Candidate components:', 'bold')} ({len(candidates)})")
        for name in candidates[:12]:
            print(f"    - {name}")
        if len(candidates) > 12:
            print(f"    ... and {len(candidates) - 12} more")

    if result.top is not None:
        if result.top.checks:
            print(f"\n  {c('Constraint checks:', 'bold')}")
            for check in result.top.checks:
                mark = c("✓", "green") if check.passed else c("✗", "red")
                print(f"    {mark} {check.kind:9s} {check.element:8s} {check.detail}")
        if result.top.unevaluable_elements:
            print(
                f"\n  {c('Unevaluable (not analysed, cannot confirm):', 'yellow')} "
                f"{', '.join(result.top.unevaluable_elements)}"
            )
        if result.top.unexplained_elements:
            print(
                f"\n  {c('Unexplained (measured, out of band, not decisive):', 'yellow')} "
                f"{', '.join(result.top.unexplained_elements)}"
            )

    if result.caveats:
        print(f"\n  {c('Caveats:', 'bold')}")
        for caveat in result.caveats:
            print(f"    - {caveat}")

    print()


def display_batch_results(results: List[Prediction], spectra: List[Dict[str, Any]]):
    """Display batch prediction results in a summary table."""
    print(f"\n  {c('Batch Identification Results', 'bold')} ({len(results)} samples)")
    print(c("  " + "=" * 60, "dim"))

    headers = ["#", "Label", "Decision", "Family", "Compatibility", "Margin"]
    rows = []

    for i, (result, spectrum) in enumerate(zip(results, spectra), start=1):
        label = spectrum.get("label", f"Sample {i}")
        rows.append([
            str(i),
            label[:20],
            result.decision.value,
            (result.top.label[:26] if result.top else "-"),
            f"{result.top.compatibility:.1%}" if result.top else "-",
            f"{result.margin:.3f}",
        ])

    print_table(headers, rows)

    identified = sum(1 for r in results if r.decision.value == "identified")
    ambiguous = sum(1 for r in results if r.decision.value == "ambiguous")
    unknown = sum(1 for r in results if r.decision.value == "unknown")

    print(f"\n  {c('Summary:', 'bold')}")
    print(f"    Identified:  {c(str(identified), 'green')}")
    print(f"    Ambiguous:   {c(str(ambiguous), 'yellow')}")
    print(f"    Unknown:     {c(str(unknown), 'red')}")
    print()


def display_families_list(kb: KnowledgeBase):
    """List every material family in the knowledge base."""
    print(f"\n  {c('Material Families', 'bold')} ({len(kb.families)} total)")
    print(c("  " + "=" * 70, "dim"))

    headers = ["ID", "Label", "Spectra", "Components", "Provisional"]
    rows = []
    for fid, fam in kb.families.items():
        rows.append([
            fid,
            fam.get("label", "")[:34],
            str(fam.get("n_spectra", 0)),
            str(fam.get("n_components", 0)),
            "yes" if fam.get("provisional") else "no",
        ])
    print_table(headers, rows)
    print()


def display_family_info(kb: KnowledgeBase, family_id: str):
    """Show detail for one family: bands, ratios, components."""
    fam = kb.families.get(family_id)
    if not fam:
        print(c(f"  No family found with id '{family_id}'", "yellow"))
        print(f"  Available: {', '.join(sorted(kb.families))}")
        return

    print(f"\n  {c(fam.get('label', family_id), 'bold')}  ({family_id})")
    print(c("  " + "-" * 60, "dim"))
    if fam.get("grade_hint"):
        print(f"  Grade hint:     {fam['grade_hint']}")
    print(f"  Discriminators: {', '.join(fam.get('discriminators', []))}")
    if fam.get("provisional"):
        print(c("  PROVISIONAL: rests on limited reference data.", "yellow"))
    if fam.get("note"):
        print(f"  Note: {fam['note']}")

    print(f"\n  {c('Element bands (metal basis, wt%):', 'bold')}")
    headers = ["Element", "Band", "Observed", "n", "Required", "Prefer ratio"]
    rows = []
    for element, spec in sorted(fam.get("elements", {}).items()):
        rows.append([
            element,
            str(spec.get("band_wt", [])),
            str(spec.get("observed_wt", [])),
            str(spec.get("n_spectra", 0)),
            "yes" if spec.get("required") else "no",
            "yes" if spec.get("prefer_ratio") else "no",
        ])
    if rows:
        print_table(headers, rows)

    ratios = fam.get("ratios", [])
    if ratios:
        print(f"\n  {c('Ratio gates:', 'bold')}")
        for r in ratios:
            print(f"    {r['ratio']}: [{r.get('min')}, {r.get('max')}]  - {r.get('rationale', '')}")

    components = fam.get("components", [])
    if components:
        print(f"\n  {c('Candidate components:', 'bold')} ({len(components)})")
        for name in components:
            print(f"    - {name}")
    print()


def display_engine_info(kb: KnowledgeBase):
    """Display information about the loaded knowledge base."""
    print(f"\n  {c('Knowledge Base Info', 'bold')}")
    print(c("  " + "-" * 40, "dim"))
    print(f"  Version:            {kb.version}")
    print(f"  Families:           {len(kb.families)}")
    print(f"  Components tracked: {len(kb.components)}")
    print()
    for caveat in kb.caveats:
        print(f"  - {caveat}")
    print()


# --------------------------------------------------------------------------
# Interactive mode
# --------------------------------------------------------------------------

def interactive_mode(kb: KnowledgeBase):
    """Run the interactive identification loop."""
    print(c("  Enter element compositions to identify the material family.", "dim"))
    print(c("  Format: Element1=Value1,Element2=Value2,...", "dim"))
    print(c("  Example: Cr=17.5,Ni=8.5,Mn=1.5,Si=0.4", "dim"))
    print(c("  A '-' value means 'analysed, not detected' (not the same as 0).", "dim"))
    print(c("  Commands: 'info', 'families', 'help', 'q' to quit", "dim"))
    print()

    while True:
        try:
            user_input = input(c("  > ", "bold")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd in ("q", "quit", "exit"):
            break
        elif cmd == "info":
            display_engine_info(kb)
            continue
        elif cmd == "families":
            display_families_list(kb)
            continue
        elif cmd == "help":
            print(c("\n  Available commands:", "bold"))
            print("    Element=Value,...  - Identify material from element composition")
            print("    info              - Show knowledge base information")
            print("    families          - List all material families")
            print("    help              - Show this help message")
            print("    q / quit / exit   - Exit the application")
            print()
            continue

        values = parse_element_string(user_input)
        if not values:
            print(c("  No valid element values found. Use format: Cr=17.5,Ni=8.5", "yellow"))
            continue

        print(c(f"  Input: {values}", "dim"))
        result = predict_spectrum(values, analysed_elements=list(values), knowledge=kb)
        display_prediction(result)


# --------------------------------------------------------------------------
# CLI argument handling
# --------------------------------------------------------------------------

def print_help():
    """Print usage help."""
    print("""
Usage: python app_rule.py [OPTIONS]

Options:
  --predict "El=Val,..."    Identify material family from element composition
  --batch FILE              Identify the family for every spectrum in a JSON file
  --list-families           List all known material families
  --family-info "ID"        Show element bands, ratios and candidates for one family
  --info                    Show knowledge base information
  --help, -h                Show this help message

Interactive mode:
  python app_rule.py        Starts interactive prompt for identification

Examples:
  python app_rule.py --predict "Cr=17.5,Ni=8.5,Mn=1.5,Si=0.4"
  python app_rule.py --predict "Cu=45.0,Sn=5.0,Zn=2.0"
  python app_rule.py --batch spectra.json
  python app_rule.py --list-families
  python app_rule.py --family-info F4
""")


def main():
    """Main entry point - parse arguments and dispatch."""
    args = sys.argv[1:]

    try:
        kb = get_knowledge_base()
    except FileNotFoundError as e:
        print(c(f"  ERROR: {e}", "red"))
        sys.exit(1)
    except Exception as e:
        print(c(f"  ERROR: Failed to load knowledge base: {e}", "red"))
        sys.exit(1)

    if "--help" in args or "-h" in args:
        print_help()
        return

    if "--info" in args:
        print_banner()
        display_engine_info(kb)
        return

    if "--list-families" in args:
        print_banner()
        display_families_list(kb)
        return

    if "--family-info" in args:
        idx = args.index("--family-info")
        if idx + 1 < len(args):
            print_banner()
            display_family_info(kb, args[idx + 1])
        else:
            print(c("  ERROR: --family-info requires a family id", "red"))
            sys.exit(1)
        return

    if "--predict" in args:
        idx = args.index("--predict")
        if idx + 1 < len(args):
            element_str = args[idx + 1]
            print_banner()
            values = parse_element_string(element_str)
            if not values:
                print(c("  ERROR: No valid element values parsed.", "red"))
                print(c("  Use format: Element=Value,Element=Value,...", "dim"))
                sys.exit(1)
            print(c(f"  Input: {values}", "dim"))
            result = predict_spectrum(values, analysed_elements=list(values), knowledge=kb)
            display_prediction(result)
        else:
            print(c("  ERROR: --predict requires an element string", "red"))
            sys.exit(1)
        return

    if "--batch" in args:
        idx = args.index("--batch")
        if idx + 1 < len(args):
            batch_file = args[idx + 1]
            print_banner()
            try:
                spectra = load_batch_file(batch_file)
            except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
                print(c(f"  ERROR: {e}", "red"))
                sys.exit(1)

            samples = [s.get("values", s) for s in spectra]
            results = [
                predict_spectrum(sample, analysed_elements=list(sample), knowledge=kb)
                for sample in samples
            ]
            display_batch_results(results, spectra)

            for i, (result, spectrum) in enumerate(zip(results, spectra), start=1):
                label = spectrum.get("label", f"Sample {i}")
                display_prediction(result, label=label)
        else:
            print(c("  ERROR: --batch requires a file path", "red"))
            sys.exit(1)
        return

    # No arguments - interactive mode
    print_banner()
    display_engine_info(kb)
    interactive_mode(kb)
    print(c("\n  Goodbye.\n", "cyan"))


if __name__ == "__main__":
    main()
