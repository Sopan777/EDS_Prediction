"""
app_rule.py
===========
Terminal application for EDS component prediction using the rule-based engine.

This tool accepts element composition values (weight percentages) and predicts
the most likely component using interpretable IF/THEN rules rather than ML
models. It supports both single predictions and batch mode.

Usage:

    # Interactive mode - follow prompts
    python app_rule.py

    # Single prediction from command line
    python app_rule.py --predict "Cr=17.5,Ni=8.5,Mn=1.5,Si=0.4"

    # Batch prediction from a JSON file
    python app_rule.py --batch spectra.json

    # Show all available rules
    python app_rule.py --list-rules

    # Show rules for a specific class
    python app_rule.py --rules-for "Armature Bolt"

This is a terminal-only tool (no web UI). It requires rule_engine/ and
config.py in the same folder.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import config
except ImportError:
    print("ERROR: config.py not found. Put app_rule.py in the project root folder.")
    sys.exit(1)

try:
    from rule_engine.engine import RuleEngine
    from rule_engine.models import PredictionResult
    from rule_engine.preprocessing import FEATURE_COLUMNS
except ImportError as e:
    print(f"ERROR: Could not import rule_engine: {e}")
    print("Make sure rule_engine/ is in the same folder as app_rule.py.")
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
    print(c("  Rule-Based EDS Component Prediction Engine", "bold"))
    print(c("  Interpretable IF/THEN rules for element composition classification.", "dim"))
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
        return left + mid.join("\u2500" * (w + 2) for w in widths) + right

    def row_line(cells):
        parts = []
        for cell, w in zip(cells, widths):
            pad = w - _visible_len(cell)
            parts.append(" " + cell + " " * (pad + 1))
        return "\u2502" + "\u2502".join(parts) + "\u2502"

    print(sep("\u250c", "\u252c", "\u2510"))
    print(row_line([c(h, "cyan") for h in headers]))
    print(sep("\u251c", "\u253c", "\u2524"))
    for str_row in str_rows:
        print(row_line(str_row))
    print(sep("\u2514", "\u2534", "\u2518"))


# --------------------------------------------------------------------------
# Parsing helpers
# --------------------------------------------------------------------------

def parse_element_string(element_str: str) -> Dict[str, float]:
    """
    Parse element values from a comma-separated string.

    Format: "Cr=17.5,Ni=8.5,Mn=1.5" or "Cr:17.5,Ni:8.5,Mn:1.5"
    """
    values = {}
    parts = element_str.strip().split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Support both = and : as separators
        if "=" in part:
            key, val = part.split("=", 1)
        elif ":" in part:
            key, val = part.split(":", 1)
        else:
            print(c(f"  WARNING: Skipping invalid part '{part}' (use Element=Value format)", "yellow"))
            continue
        key = key.strip()
        try:
            values[key] = float(val.strip())
        except ValueError:
            print(c(f"  WARNING: Non-numeric value for '{key}': '{val.strip()}' (using 0.0)", "yellow"))
            values[key] = 0.0
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

def format_status(status: str) -> str:
    """Format prediction status with color."""
    if status == "matched":
        return c(status, "green")
    elif status == "low_confidence":
        return c(status, "yellow")
    elif status == "no_match":
        return c(status, "red")
    return status


def display_prediction(result: PredictionResult, engine: RuleEngine, label: str = ""):
    """Display a single prediction result in a readable format."""
    if label:
        print(f"\n  {c(label, 'bold')}")
        print(c("  " + "-" * 50, "dim"))

    # Main result
    print(f"  {c('Prediction:', 'bold')}  {result.prediction}")
    print(f"  {c('Confidence:', 'bold')}  {result.confidence:.2%}")
    print(f"  {c('Status:', 'bold')}      {format_status(result.status)}")
    print(f"  {c('Rule ID:', 'bold')}     {result.rule_id or 'N/A'}")

    # Matched conditions
    if result.matched_conditions:
        print(f"\n  {c('Matched Conditions:', 'bold')}")
        for cond in result.matched_conditions:
            feature = cond["feature"]
            operator = cond["operator"]
            threshold = cond["threshold"]
            actual = cond["actual_value"]
            check = c("\u2713", "green")
            print(f"    {check} {feature} {operator} {threshold:.2f}  (actual: {actual:.2f})")

    # Other matches
    if len(result.all_matches) > 1:
        print(f"\n  {c('Other matching rules:', 'dim')} ({len(result.all_matches) - 1} additional)")
        for match in result.all_matches[1:4]:  # Show up to 3 alternatives
            print(f"    - {match.rule.prediction} "
                  f"(confidence: {match.rule.confidence:.2%}, rule: {match.rule.id})")
        if len(result.all_matches) > 4:
            print(f"    ... and {len(result.all_matches) - 4} more")

    # Full explanation
    print(f"\n  {c('Explanation:', 'bold')}")
    explanation = engine.explain_prediction(result)
    for line in explanation.split("\n"):
        print(f"    {line}")

    print()


def display_batch_results(
    results: List[PredictionResult],
    spectra: List[Dict[str, Any]],
    engine: RuleEngine,
):
    """Display batch prediction results in a summary table."""
    print(f"\n  {c('Batch Prediction Results', 'bold')} ({len(results)} samples)")
    print(c("  " + "=" * 60, "dim"))

    headers = ["#", "Label", "Prediction", "Confidence", "Status", "Rule"]
    rows = []

    for i, (result, spectrum) in enumerate(zip(results, spectra), start=1):
        label = spectrum.get("label", f"Sample {i}")
        rows.append([
            str(i),
            label[:20],
            result.prediction,
            f"{result.confidence:.2%}",
            result.status,
            result.rule_id or "N/A",
        ])

    print_table(headers, rows)

    # Summary statistics
    matched = sum(1 for r in results if r.status == "matched")
    low_conf = sum(1 for r in results if r.status == "low_confidence")
    no_match = sum(1 for r in results if r.status == "no_match")

    print(f"\n  {c('Summary:', 'bold')}")
    print(f"    Matched:         {c(str(matched), 'green')}")
    print(f"    Low Confidence:  {c(str(low_conf), 'yellow')}")
    print(f"    No Match:        {c(str(no_match), 'red')}")
    print()


def display_rules_list(engine: RuleEngine, class_filter: Optional[str] = None):
    """Display available rules, optionally filtered by class."""
    if class_filter:
        rules = engine.get_rules_for_class(class_filter)
        if not rules:
            print(c(f"  No rules found for class: '{class_filter}'", "yellow"))
            print(f"  Available classes: {', '.join(engine.classes[:10])}...")
            return
        print(f"\n  {c(f'Rules for: {class_filter}', 'bold')}")
    else:
        rules = engine._rules
        print(f"\n  {c('All Rules', 'bold')} ({len(rules)} total)")

    print(c("  " + "=" * 60, "dim"))

    headers = ["Rule ID", "Prediction", "Confidence", "Support", "Val. Acc.", "Conditions"]
    rows = []

    for rule in rules:
        cond_summary = "; ".join(
            f"{cd.feature}{cd.operator}{cd.threshold:.1f}"
            for cd in rule.conditions[:3]
        )
        if len(rule.conditions) > 3:
            cond_summary += f" +{len(rule.conditions) - 3} more"

        rows.append([
            rule.id,
            rule.prediction[:22],
            f"{rule.confidence:.2%}",
            str(rule.support),
            f"{rule.validation_accuracy:.2%}",
            cond_summary[:40],
        ])

    print_table(headers, rows)
    print()


def display_engine_info(engine: RuleEngine):
    """Display information about the loaded rule engine."""
    print(f"\n  {c('Rule Engine Info', 'bold')}")
    print(c("  " + "-" * 40, "dim"))
    print(f"  Rules loaded:       {engine.rules_count}")
    print(f"  Classes covered:    {len(engine.classes)}")
    print(f"  Confidence threshold: {engine.confidence_threshold:.2%}")
    if engine.ruleset:
        print(f"  Version:            {engine.ruleset.version}")
        print(f"  Generated:          {engine.ruleset.generated_at}")
        print(f"  Algorithm:          {engine.ruleset.algorithm}")
        print(f"  Validation score:   {engine.ruleset.validation_score:.2%}")
    print(f"  Features:           {', '.join(FEATURE_COLUMNS)}")
    print()


# --------------------------------------------------------------------------
# Interactive mode
# --------------------------------------------------------------------------

def interactive_mode(engine: RuleEngine):
    """Run the interactive prediction loop."""
    print(c("  Enter element compositions to predict components.", "dim"))
    print(c("  Format: Element1=Value1,Element2=Value2,...", "dim"))
    print(c("  Example: Cr=17.5,Ni=8.5,Mn=1.5,Si=0.4", "dim"))
    print(c("  Commands: 'info', 'rules', 'help', 'q' to quit", "dim"))
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
            display_engine_info(engine)
            continue
        elif cmd == "rules":
            display_rules_list(engine)
            continue
        elif cmd == "help":
            print(c("\n  Available commands:", "bold"))
            print("    Element=Value,...  - Predict component from element composition")
            print("    info              - Show rule engine information")
            print("    rules             - List all loaded rules")
            print("    help              - Show this help message")
            print("    q / quit / exit   - Exit the application")
            print()
            continue

        # Parse as element values and predict
        values = parse_element_string(user_input)
        if not values:
            print(c("  No valid element values found. Use format: Cr=17.5,Ni=8.5", "yellow"))
            continue

        # Show what we parsed
        print(c(f"  Input: {values}", "dim"))

        # Predict
        result = engine.predict(values)
        display_prediction(result, engine)


# --------------------------------------------------------------------------
# CLI argument handling
# --------------------------------------------------------------------------

def print_help():
    """Print usage help."""
    print("""
Usage: python app_rule.py [OPTIONS]

Options:
  --predict "El=Val,..."    Predict component from element composition string
  --batch FILE              Predict components for all spectra in a JSON file
  --list-rules              List all loaded rules
  --rules-for "CLASS"       Show rules for a specific component class
  --info                    Show rule engine information
  --threshold FLOAT         Set confidence threshold (default: from config)
  --help, -h                Show this help message

Interactive mode:
  python app_rule.py        Starts interactive prompt for predictions

Examples:
  python app_rule.py --predict "Cr=17.5,Ni=8.5,Mn=1.5,Si=0.4"
  python app_rule.py --predict "Cu=45.0,Sn=5.0,Zn=2.0"
  python app_rule.py --batch spectra.json
  python app_rule.py --list-rules
  python app_rule.py --rules-for "Armature Bolt"
""")


def main():
    """Main entry point - parse arguments and dispatch."""
    args = sys.argv[1:]

    # Parse threshold if provided
    threshold = None
    if "--threshold" in args:
        idx = args.index("--threshold")
        if idx + 1 < len(args):
            try:
                threshold = float(args[idx + 1])
            except ValueError:
                print(c("  ERROR: --threshold requires a numeric value", "red"))
                sys.exit(1)
            args = args[:idx] + args[idx + 2:]
        else:
            print(c("  ERROR: --threshold requires a value", "red"))
            sys.exit(1)

    # Initialize engine
    try:
        engine_kwargs = {}
        if threshold is not None:
            engine_kwargs["confidence_threshold"] = threshold
        engine = RuleEngine(**engine_kwargs)
    except FileNotFoundError as e:
        print(c(f"  ERROR: {e}", "red"))
        print(c("  Run `python training/train_rules.py` to generate the rules file.", "dim"))
        sys.exit(1)
    except Exception as e:
        print(c(f"  ERROR: Failed to initialize rule engine: {e}", "red"))
        sys.exit(1)

    # Handle --help
    if "--help" in args or "-h" in args:
        print_help()
        return

    # Handle --info
    if "--info" in args:
        print_banner()
        display_engine_info(engine)
        return

    # Handle --list-rules
    if "--list-rules" in args:
        print_banner()
        display_rules_list(engine)
        return

    # Handle --rules-for
    if "--rules-for" in args:
        idx = args.index("--rules-for")
        if idx + 1 < len(args):
            class_name = args[idx + 1]
            print_banner()
            display_rules_list(engine, class_filter=class_name)
        else:
            print(c("  ERROR: --rules-for requires a class name", "red"))
            sys.exit(1)
        return

    # Handle --predict
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
            result = engine.predict(values)
            display_prediction(result, engine)
        else:
            print(c("  ERROR: --predict requires an element string", "red"))
            sys.exit(1)
        return

    # Handle --batch
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

            # Run predictions
            samples = [s.get("values", s) for s in spectra]
            results = engine.predict_batch(samples)
            display_batch_results(results, spectra, engine)

            # Also show detailed results for each
            for i, (result, spectrum) in enumerate(zip(results, spectra), start=1):
                label = spectrum.get("label", f"Sample {i}")
                display_prediction(result, engine, label=label)
        else:
            print(c("  ERROR: --batch requires a file path", "red"))
            sys.exit(1)
        return

    # No arguments - interactive mode
    print_banner()
    display_engine_info(engine)
    interactive_mode(engine)
    print(c("\n  Goodbye.\n", "cyan"))


if __name__ == "__main__":
    main()
