"""
Synthetic Rate Monitor (TODO #49)
===================================
Tracks the fraction of qualifying bets / predictions that are based on
*synthetic* (simulated) data vs *real* historical outcomes, and raises
alerts when that fraction exceeds safety thresholds.

Why this matters
----------------
The profitability validation suite (PROF-001 … PROF-005) uses synthetic
match generation when real historical data is insufficient.  A high
synthetic rate means the live-trading verdict is built on simulated
performance — not real.  This monitor makes that risk *visible* and
*actionable*.

Alert levels
------------
``SAFE``    – real-data fraction is acceptable (< warn threshold)
``WARNING`` – synthetic rate is getting high; flag for manual review
``CRITICAL``– synthetic rate so high that live-trade decisions are unreliable

Typical usage
-------------
    monitor = SyntheticRateMonitor()
    monitor.record(is_synthetic=False, league="premier-league")
    monitor.record(is_synthetic=True,  league="premier-league")
    alert = monitor.current_alert()
    if alert.level == AlertLevel.CRITICAL:
        raise RuntimeError("Too few real bets to trust live verdict")
"""

from __future__ import annotations

import json
import os
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums / constants
# ---------------------------------------------------------------------------

class AlertLevel(str, Enum):
    SAFE     = "SAFE"
    WARNING  = "WARNING"
    CRITICAL = "CRITICAL"


#: Default thresholds (synthetic fraction)
DEFAULT_WARN_THRESHOLD     = 0.50   # > 50 % synthetic → WARNING
DEFAULT_CRITICAL_THRESHOLD = 0.80   # > 80 % synthetic → CRITICAL
DEFAULT_MIN_REAL_FOR_LIVE  = 100    # need at least 100 real bets before live trading
DEFAULT_WINDOW             = 500    # rolling window size


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SyntheticRateAlert:
    """Current alert state from the synthetic rate monitor."""
    level:             AlertLevel
    synthetic_count:   int
    real_count:        int
    total_count:       int
    synthetic_rate:    float          # 0-1
    real_rate:         float          # 0-1
    min_real_met:      bool           # True if real ≥ min_real_for_live
    message:           str
    checked_at:        str            # ISO-8601
    per_league:        Dict[str, dict] = field(default_factory=dict)

    def is_safe_for_live(self) -> bool:
        return self.level == AlertLevel.SAFE and self.min_real_met

    def summary(self) -> str:
        icon = {"SAFE": "✓", "WARNING": "⚠", "CRITICAL": "✗"}.get(self.level, "?")
        return (
            f"[{icon} {self.level}] "
            f"{self.real_count}/{self.total_count} real "
            f"({self.real_rate:.1%}) | "
            f"synthetic {self.synthetic_rate:.1%} | "
            f"min-real {'MET' if self.min_real_met else 'NOT MET'}"
        )


# ---------------------------------------------------------------------------
# Core monitor
# ---------------------------------------------------------------------------

class SyntheticRateMonitor:
    """
    Rolling-window monitor for the synthetic vs real data ratio.

    Parameters
    ----------
    warn_threshold      : synthetic fraction above which WARNING fires (0.50)
    critical_threshold  : synthetic fraction above which CRITICAL fires (0.80)
    min_real_for_live   : minimum number of real bets before live-trading ok (100)
    window              : rolling window size (500)
    persist_path        : optional JSON file for state persistence
    """

    def __init__(
        self,
        warn_threshold:    float = DEFAULT_WARN_THRESHOLD,
        critical_threshold: float = DEFAULT_CRITICAL_THRESHOLD,
        min_real_for_live: int   = DEFAULT_MIN_REAL_FOR_LIVE,
        window:            int   = DEFAULT_WINDOW,
        persist_path:      Optional[str] = None,
    ) -> None:
        self.warn_threshold     = warn_threshold
        self.critical_threshold = critical_threshold
        self.min_real_for_live  = min_real_for_live
        self.window             = window
        self.persist_path       = persist_path

        # Rolling buffer: each entry is (is_synthetic: bool, league: str)
        self._buffer: deque = deque(maxlen=window)

        # Per-league accumulators (all-time, not just rolling window)
        self._league_real:      Dict[str, int] = {}
        self._league_synthetic: Dict[str, int] = {}

        # All-time totals (supplement rolling window stats)
        self._total_real      = 0
        self._total_synthetic = 0

        if persist_path and os.path.isfile(persist_path):
            self._load(persist_path)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(
        self,
        is_synthetic: bool,
        league:       Optional[str] = None,
        timestamp:    Optional[str] = None,
    ) -> None:
        """
        Record one bet/prediction.

        Parameters
        ----------
        is_synthetic : True if based on synthetic/simulated data
        league       : league code (optional, for per-league breakdown)
        timestamp    : ISO-8601 string (optional, informational only)
        """
        lg = league or "_all"
        self._buffer.append((is_synthetic, lg))

        # Per-league totals
        if is_synthetic:
            self._league_synthetic[lg] = self._league_synthetic.get(lg, 0) + 1
            self._total_synthetic += 1
        else:
            self._league_real[lg] = self._league_real.get(lg, 0) + 1
            self._total_real += 1

    def record_batch(self, records: List[dict]) -> None:
        """
        Record multiple bets at once.
        Each record must have ``is_synthetic`` key; ``league`` is optional.

        Example::
            monitor.record_batch([
                {"is_synthetic": False, "league": "premier-league"},
                {"is_synthetic": True,  "league": "la-liga"},
            ])
        """
        for rec in records:
            self.record(
                is_synthetic=bool(rec["is_synthetic"]),
                league=rec.get("league"),
            )

    # ------------------------------------------------------------------
    # Alert computation
    # ------------------------------------------------------------------

    def current_alert(self) -> SyntheticRateAlert:
        """Compute and return the current alert state."""
        n_total     = len(self._buffer)
        n_synthetic = sum(1 for is_s, _ in self._buffer if is_s)
        n_real      = n_total - n_synthetic

        synth_rate = n_synthetic / n_total if n_total > 0 else 0.0
        real_rate  = 1.0 - synth_rate

        min_real_met = self._total_real >= self.min_real_for_live

        if synth_rate >= self.critical_threshold:
            level  = AlertLevel.CRITICAL
            msg = (
                f"CRITICAL: {synth_rate:.1%} of recent {n_total} bets are synthetic. "
                f"Live-trading verdict is UNRELIABLE. "
                f"Collect at least {self.min_real_for_live} real bets (have {self._total_real})."
            )
        elif synth_rate >= self.warn_threshold:
            level = AlertLevel.WARNING
            msg = (
                f"WARNING: {synth_rate:.1%} of recent {n_total} bets are synthetic. "
                f"Real bets: {self._total_real}/{self.min_real_for_live} required."
            )
        else:
            level = AlertLevel.SAFE
            msg = (
                f"SAFE: {synth_rate:.1%} synthetic rate in last {n_total} bets. "
                f"Real bets: {self._total_real}."
            )
        if not min_real_met and level == AlertLevel.SAFE:
            level = AlertLevel.WARNING
            msg += f"  (min real-data bets not yet met: {self._total_real}/{self.min_real_for_live})"

        # Per-league breakdown
        per_league: Dict[str, dict] = {}
        all_leagues = set(self._league_real) | set(self._league_synthetic)
        for lg in sorted(all_leagues):
            r = self._league_real.get(lg, 0)
            s = self._league_synthetic.get(lg, 0)
            t = r + s
            per_league[lg] = {
                "real": r, "synthetic": s, "total": t,
                "synthetic_rate": s / t if t > 0 else 0.0,
            }

        return SyntheticRateAlert(
            level=level,
            synthetic_count=n_synthetic,
            real_count=n_real,
            total_count=n_total,
            synthetic_rate=synth_rate,
            real_rate=real_rate,
            min_real_met=min_real_met,
            message=msg,
            checked_at=datetime.now(timezone.utc).isoformat(),
            per_league=per_league,
        )

    # ------------------------------------------------------------------
    # Stats helpers
    # ------------------------------------------------------------------

    def rolling_synthetic_rate(self) -> Optional[float]:
        """Synthetic fraction in the current rolling window (None if empty)."""
        n = len(self._buffer)
        if n == 0:
            return None
        return sum(1 for is_s, _ in self._buffer if is_s) / n

    def total_real(self) -> int:
        return self._total_real

    def total_synthetic(self) -> int:
        return self._total_synthetic

    def n_recorded(self) -> int:
        """Total all-time records (not capped by window)."""
        return self._total_real + self._total_synthetic

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Optional[str] = None) -> None:
        """Persist monitor state to JSON."""
        target = path or self.persist_path
        if not target:
            return
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        state = {
            "total_real":       self._total_real,
            "total_synthetic":  self._total_synthetic,
            "league_real":      self._league_real,
            "league_synthetic": self._league_synthetic,
            "window_size":      self.window,
        }
        with open(target, "w") as fh:
            json.dump(state, fh, indent=2)

    def _load(self, path: str) -> None:
        try:
            with open(path) as fh:
                state = json.load(fh)
            self._total_real      = int(state.get("total_real", 0))
            self._total_synthetic = int(state.get("total_synthetic", 0))
            self._league_real     = {k: int(v) for k, v in state.get("league_real", {}).items()}
            self._league_synthetic = {k: int(v) for k, v in state.get("league_synthetic", {}).items()}
        except Exception:   # noqa: BLE001
            pass  # corrupt state — start fresh

    def load(self, path: Optional[str] = None) -> None:
        """Restore state from JSON."""
        target = path or self.persist_path
        if target and os.path.isfile(target):
            self._load(target)

    def reset(self) -> None:
        """Clear all in-memory state."""
        self._buffer.clear()
        self._league_real.clear()
        self._league_synthetic.clear()
        self._total_real      = 0
        self._total_synthetic = 0
