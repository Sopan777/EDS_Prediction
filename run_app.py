"""
run_app.py
==========
One-click launcher for Spectral Lab - MaterialID v2.4 (Streamlit Unified App).
Starts the unified Streamlit application and opens the browser.

Usage:
    python run_app.py
    python run_app.py --port 5000
    streamlit run app.py
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
APP_FILE = REPO_ROOT / "app.py"


def main():
    parser = argparse.ArgumentParser(description="Spectral Lab - MaterialID Launcher")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on (default: 5000)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(APP_FILE),
        f"--server.port={args.port}",
    ]
    if args.no_browser:
        cmd.append("--server.headless=true")

    print("\n" + "=" * 65)
    print("  SPECTRAL LAB - MATERIAL-FAMILY IDENTIFICATION PIPELINE v2.4")
    print("  Unified Streamlit Application (Deterministic Rule Engine)")
    print("=" * 65)
    print(f"\n  Starting application on: http://localhost:{args.port}")
    print("  Press Ctrl+C to terminate the application.\n")

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nSpectral Lab application terminated.")


if __name__ == "__main__":
    main()
