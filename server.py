"""
Root entry compatibility shim for backend.server.
Allows running `python server.py` or `from server import app`.
"""
import sys
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.server import app, get_db_connection, main  # noqa: E402

if __name__ == "__main__":
    main()
