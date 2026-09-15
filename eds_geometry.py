"""
Compatibility shim: re-exports from backend.ingestion.eds_geometry.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.ingestion.eds_geometry import *  # noqa: F401, F403
from backend.ingestion.eds_geometry import available, extract_tables  # noqa: F401
