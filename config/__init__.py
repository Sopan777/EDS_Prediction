import importlib.util
from pathlib import Path

# Preserve root config.py exports for rule_engine compatibility
_config_py = Path(__file__).resolve().parent.parent / "config.py"
if _config_py.exists():
    _spec = importlib.util.spec_from_file_location("_legacy_config", _config_py)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    for _k, _v in _mod.__dict__.items():
        if not _k.startswith("__"):
            globals()[_k] = _v
