#!/usr/bin/env python3
"""Regenerate recent reports and prune old runs.

Usage: python scripts/regenerate_reports.py --leagues la-liga premier-league
or: python scripts/regenerate_reports.py --all
"""

import argparse
import subprocess
import time
from pathlib import Path
import json
import os
import sys

PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports" / "leagues"


from typing import Optional, Union


def prune_old_reports(
    league: str,
    keep: int = 50,
    debug: bool = False,
    base_dir: Optional[Union[str, Path]] = None,
) -> int:
    base = Path(base_dir) if base_dir else REPORTS_DIR
    league_dir = base / league / "matches"
    if not league_dir.exists():
        return 0
    # Collect match dirs and their match_date (from prediction.json)
    items = []
    for d in league_dir.iterdir():
        if not d.is_dir():
            continue
        pred = d / "prediction.json"
        if not pred.exists():
            items.append((d, ""))
            continue
        try:
            j = json.loads(pred.read_text(encoding="utf-8"))
            md = j.get("match_date") or j.get("date") or ""
        except Exception:
            md = ""
        items.append((d, md))
    # sort by match_date desc (newest first)
    items.sort(key=lambda x: x[1], reverse=True)
    removed = 0
    for d, md in items[keep:]:
        # be conservative: only remove if folder contains prediction.json
        if (d / "prediction.json").exists():
            for f in d.iterdir():
                try:
                    if f.is_file():
                        f.unlink()
                except Exception:
                    pass
            try:
                d.rmdir()
                removed += 1
            except Exception:
                pass
    if debug:
        print(f"Pruned {removed} old reports from {league}")
    return removed


def regenerate_for_league(
    league: str, count: int = 5, delay_sec: int = 60, debug: bool = False
):
    # Run generates and wait between runs
    for i in range(count):
        cmd = [
            sys.executable,
            "generate_fast_reports.py",
            "generate",
            str(1),
            "matches",
            "for",
            league,
        ]
        env = os.environ.copy()
        # Ensure subprocess Python uses UTF-8 I/O to avoid UnicodeEncodeError on Windows consoles
        env["PYTHONUTF8"] = "1"
        try:
            if debug:
                print("Running:", " ".join(cmd))
            subprocess.run(cmd, check=False, env=env)
        except Exception as e:
            if debug:
                print(f"Regenerate command failed: {e}")
        time.sleep(delay_sec)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--leagues", nargs="*", help="List of leagues to regenerate")
    parser.add_argument(
        "--all", action="store_true", help="Regenerate for all detected leagues"
    )
    parser.add_argument("--prune-keep", type=int, default=50)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--delay", type=int, default=60)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    leagues = args.leagues or []
    if args.all:
        detected = [p.name for p in REPORTS_DIR.iterdir() if p.is_dir()]
        leagues = detected

    for league in leagues:
        if args.debug:
            print(f"Processing league: {league}")
        prune_old_reports(league, keep=args.prune_keep, debug=args.debug)
        regenerate_for_league(
            league, count=args.count, delay_sec=args.delay, debug=args.debug
        )


if __name__ == "__main__":
    main()
