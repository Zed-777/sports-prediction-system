"""Shim to expose legacy AI ML predictor module at top-level for optional imports.
This loads the implementation from `legacy_files/ai_ml_predictor.py` and re-exports
the main classes expected by other modules. This loader is defensive: if the
legacy module cannot be found or loaded, it leaves the exported symbols as None.
"""
import importlib.util
import os
from types import ModuleType

_path = os.path.join(os.path.dirname(__file__), 'legacy_files', 'ai_ml_predictor.py')
_spec = importlib.util.spec_from_file_location('legacy_ai_ml_predictor', _path)
_legacy: ModuleType | None = None
if _spec and _spec.loader:
    _legacy = importlib.util.module_from_spec(_spec)
    try:
        _spec.loader.exec_module(_legacy)  # type: ignore[attr-defined]
    except Exception:
        _legacy = None

# Re-export expected symbols (None if not available)
try:
    AIMLPredictor = _legacy.AIMLPredictor if _legacy is not None else None
except Exception:
    AIMLPredictor = None
