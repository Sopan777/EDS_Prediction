"""
Root entry compatibility shim for backend.cli.app_rule.
Allows running `python app_rule.py`.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.cli.app_rule import main  # noqa: E402

if __name__ == "__main__":
    main()
