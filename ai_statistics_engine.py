"""Lightweight shim placeholder for optional legacy component.

This module intentionally exposes a None placeholder so imports succeed in
environments where the legacy implementation is not present. The real
implementation lives under `legacy_files/` and is optional.
"""

AIStatisticsEngine = None
