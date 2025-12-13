"""Shim to expose legacy neural pattern engine from legacy_files.

Defensive loader: if the legacy module isn't available, exported symbol will be None.
"""

import importlib.util
import os
from types import ModuleType

_path = os.path.join(os.path.dirname(__file__), 'legacy_files', 'neural_pattern_engine.py')
_spec = importlib.util.spec_from_file_location('legacy_neural_pattern_engine', _path)
_legacy: ModuleType | None = None
if _spec and _spec.loader:
    _legacy = importlib.util.module_from_spec(_spec)
    try:
        _spec.loader.exec_module(_legacy)  # type: ignore[attr-defined]
    except Exception:
        _legacy = None

try:
    NeuralPatternRecognition = _legacy.NeuralPatternRecognition if _legacy is not None else None
except Exception:
    NeuralPatternRecognition = None
