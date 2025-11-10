"""Lightweight shim placeholder for optional market data connectors.

Expose a None placeholder so imports succeed in environments where the
legacy implementation under `legacy_files/` is not present.
"""

MarketDataConnector = None
