#!/usr/bin/env python3
"""Inspect debug HTML files saved by FlashScore scraper and summarize common patterns

Usage:
    python scripts/debug_flashscore_inspect.py --dir reports/debug/flashscore --out reports/metrics/flashscore_debug_summary.json
"""
import argparse
import json
from pathlib import Path


def inspect_dir(base: Path):
    files = list(base.glob("*.html"))
    summary = {"total_files": len(files), "samples": [], "patterns": {}}
    patterns_count = {}
    keywords = ["window.__", "window.__initial", "application/json", "fetch(", ".json", "data-layer", "xhr", "api", "v3.", "initialState", "content-security-policy"]
    for f in files[:200]:
        text = ""
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        lower = text.lower()
        sample = {"file": str(f.name), "length": len(text)}
        # classify
        if "<html" in lower:
            sample["type"] = "html"
        elif "window.__" in lower or "window.__initial" in lower or "initialstate" in lower:
            sample["type"] = "window_initial_state"
        elif "application/json" in lower or text.strip().startswith("{"):
            sample["type"] = "json"
        elif "<script" in lower:
            sample["type"] = "script_payload"
        else:
            sample["type"] = "other"
        summary["samples"].append(sample)
        summary["patterns"][sample["type"]] = summary["patterns"].get(sample["type"], 0) + 1

        # keyword scanning
        for kw in keywords:
            if kw in lower:
                patterns_count[kw] = patterns_count.get(kw, 0) + 1

    summary["keyword_hits"] = patterns_count
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dir", type=str, default="reports/debug/flashscore")
    p.add_argument("--out", type=str, default="reports/metrics/flashscore_debug_summary.json")
    args = p.parse_args()

    base = Path(args.dir)
    if not base.exists():
        print("No debug directory found")
        return 1

    summary = inspect_dir(base)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
