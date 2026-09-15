"""
run_app.py
==========
One-click launcher for Spectral Lab - MaterialID.
Starts the Flask server hosting the deterministic rule-based microanalysis engine
and the integrated React UI, then opens the browser.

Usage:
    python run_app.py
    python run_app.py --port 8080
"""

import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = REPO_ROOT / "frontend"
if not FRONTEND_DIR.exists():
    FRONTEND_DIR = REPO_ROOT / "spectral-lab---materialid"
FRONTEND_DIST = FRONTEND_DIR / "dist"


def ensure_frontend_built():
    """Verify frontend dependencies and build exist, installing/building if needed."""
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

    # Ensure node_modules exists
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        print("Frontend node_modules not found. Running npm install...")
        subprocess.run([npm_cmd, "install"], cwd=str(FRONTEND_DIR), check=True)
        print("Frontend dependencies installed.")

    # Ensure dist exists
    if not (FRONTEND_DIST / "index.html").exists():
        print("Frontend distribution not found. Building with Vite...")
        subprocess.run([npm_cmd, "run", "build"], cwd=str(FRONTEND_DIR), check=True)
        print("Frontend built successfully.")


def main():
    parser = argparse.ArgumentParser(description="Spectral Lab - Rule-Based MaterialID")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on (default: 5000)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    ensure_frontend_built()

    url = f"http://localhost:{args.port}"
    print("\n" + "=" * 65)
    print("  SPECTRAL LAB - MATERIAL-FAMILY IDENTIFICATION ENGINE v2.4")
    print("  Deterministic Compatibility Scoring (Rule-Based)")
    print("=" * 65)
    print(f"\n  Serving web application at: {url}")
    print("  Press Ctrl+C to terminate the server.\n")

    if not args.no_browser:
        def open_browser():
            time.sleep(1.2)
            try:
                webbrowser.open(url)
            except Exception:
                pass
        import threading
        threading.Thread(target=open_browser, daemon=True).start()

    os.environ["PORT"] = str(args.port)
    from backend.server import app
    app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
