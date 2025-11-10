"""Lightweight shim placeholder for optional legacy betting market module.

Expose a None placeholder so imports succeed in environments where the
legacy implementation under `legacy_files/` is not present. This keeps
optional dependencies from causing import-time failures.
"""

BettingMarketIntelligence = None
