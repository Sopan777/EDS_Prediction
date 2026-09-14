"""
Compatibility shim: re-exports from backend.ingestion.eds_pipeline.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.ingestion.eds_pipeline import *  # noqa: F401, F403

if __name__ == "__main__":
    import backend.ingestion.eds_pipeline as _m
    _m.main()
