"""
Compatibility shim: re-exports from backend.ingestion.eds_extractor.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.ingestion.eds_extractor import *  # noqa: F401, F403
from backend.ingestion.eds_extractor import canonical_element_symbol, extract_eds_tables  # noqa: F401

if __name__ == "__main__":
    import backend.ingestion.eds_extractor as _m
    _m.main()
