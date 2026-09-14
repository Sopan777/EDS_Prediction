"""
backend/paths.py
=================
Single place that wires this web backend to the existing eds_core project
(rule_engine, eds_extractor, eds_pipeline, config, ...) and defines where
persistent web-layer data (audit log, uploads, KB backups) lives.

Importing this module is the first thing every other backend module does,
so eds_core's sibling-relative imports ("from rule_engine...", "from config
import ...") keep working unmodified - we add eds_core/ to sys.path instead
of touching eds_core's own import style.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
EDS_CORE_DIR = ROOT_DIR / "eds_core"
FRONTEND_DIST_DIR = ROOT_DIR / "frontend" / "out"
SAMPLES_DIR = ROOT_DIR / "samples"
DATA_STORE_DIR = ROOT_DIR / "data_store"
UPLOADS_DIR = DATA_STORE_DIR / "uploads"
AUDIT_LOG_PATH = DATA_STORE_DIR / "audit_log.json"

if str(EDS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(EDS_CORE_DIR))

KNOWLEDGE_PATH = EDS_CORE_DIR / "rule_engine" / "knowledge" / "materials.json"
KNOWLEDGE_BACKUP_DIR = DATA_STORE_DIR / "kb_backups"

DATA_STORE_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
if not AUDIT_LOG_PATH.exists():
    AUDIT_LOG_PATH.write_text("[]", encoding="utf-8")
