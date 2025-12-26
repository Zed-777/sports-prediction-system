#!/usr/bin/env python3
"""
Report recent accuracy per league from data/historical/*.json

Usage:
    python scripts/report_recent_accuracy.py --recent 10
"""

import json
from pathlib import Path
from datetime import datetime
import argparse

HIST_DIR = Path(__file__).parent.parent / "data" / "historical"


def parse_date(d):
    if not d:
        return None
    try:
        return datetime.fromisoformat(d.replace("Z", "+00:00"))
    except Exception:
        try:
            return datetime.strptime(d, "%Y-%m-%dT%H:%M")
        except Exception:
            try:
                return datetime.strptime(d, "%Y-%m-%d")
            except Exception:
                return None


def derive_predicted(rec):
    pred = rec.get("prediction", {})
    reco = pred.get("predicted_outcome") or pred.get("predicted") or ""
    if reco:
        # Normalize text if it contains words
        if isinstance(reco, str):
            low = reco.lower()
            if "away" in low:
                return "away_win"
            if "home" in low:
                return "home_win"
            if "draw" in low or "tie" in low:
                return "draw"
    # Fallback: look at probs
    ph = pred.get("home_win_prob", pred.get("home_win_probability", 0))
    pd = pred.get("draw_prob", pred.get("draw_probability", 0))
    pa = pred.get("away_win_prob", pred.get("away_win_probability", 0))
    try:
        ph = float(ph)
        pd = float(pd)
        pa = float(pa)
    except Exception:
        return None
    # percentages may be >1
    if ph > 1:
        ph /= 100.0
    if pd > 1:
        pd /= 100.0
    if pa > 1:
        pa /= 100.0
    if ph > pd and ph > pa:
        return "home_win"
    if pd > pa:
        return "draw"
    return "away_win"


def format_outcome(ar):
    if not ar:
        return "N/A"
    hs = ar.get("home_score")
    as_ = ar.get("away_score")
    if hs is None or as_ is None:
        return ar.get("outcome", "N/A")
    return f"{hs}-{as_} ({ar.get('outcome', '')})"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--recent",
        type=int,
        default=10,
        help="How many recent completed matches to show per league",
    )
    args = parser.parse_args()

    files = sorted(HIST_DIR.glob("*_results.json"))
    if not files:
        print("No historical files found.")
        return

    overall = {}

    for f in files:
        league = f.name.replace("_results.json", "")
        with open(f, "r", encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except Exception:
                data = []
        # Filter completed
        completed = [r for r in data if r.get("actual_result")]
        # Enrich
        for r in completed:
            r["_parsed_date"] = (
                parse_date(r.get("match_date") or r.get("collected_at")) or datetime.min
            )
            # Derive predicted outcome if missing
            if not r.get("prediction", {}).get("predicted_outcome"):
                r["prediction"]["predicted_outcome"] = derive_predicted(r)
        completed.sort(
            key=lambda x: x.get("_parsed_date") or datetime.min, reverse=True
        )

        total = len(completed)
        correct = sum(1 for r in completed if r.get("prediction_correct"))
        exact_total = sum(1 for r in completed if r.get("exact_score_correct"))
        top3_total = sum(1 for r in completed if r.get("score_in_top3"))
        accuracy = (correct / total) if total > 0 else None

        overall[league] = {
            "total_completed": total,
            "correct": correct,
            "accuracy": accuracy,
            "exact_total": exact_total,
            "top3_total": top3_total,
            "recent_matches": [],
        }

        for r in completed[: args.recent]:
            overall[league]["recent_matches"].append(
                {
                    "match_id": r.get("match_id"),
                    "date": r.get("match_date"),
                    "teams": f"{r.get('home_team')} vs {r.get('away_team')}",
                    "predicted": r.get("prediction", {}).get("predicted_outcome"),
                    "actual": format_outcome(r.get("actual_result")),
                    "correct": bool(r.get("prediction_correct", False)),
                    "exact": bool(r.get("exact_score_correct", False)),
                    "top3": bool(r.get("score_in_top3", False)),
                }
            )

    # Print report
    print("\nRecent accuracy report:")
    print("=======================\n")
    for league, stats in sorted(overall.items()):
        print(f"League: {league}")
        print(f"  Completed matches: {stats['total_completed']}")
        if stats["accuracy"] is not None:
            print(f"  Correct: {stats['correct']} ({stats['accuracy'] * 100:.1f}%)")
        else:
            print("  Correct: N/A")
        # Exact/Top3 summary
        print(f"  Exact score correct: {stats.get('exact_total', 0)}")
        print(f"  Actual in top-3 predicted scores: {stats.get('top3_total', 0)}")
        print("  Recent matches:")
        for m in stats["recent_matches"]:
            status = "✓" if m["correct"] else "✗"
            exact_mark = "EXACT" if m.get("exact") else ""
            top3_mark = "TOP3" if m.get("top3") else ""
            markers = " ".join([x for x in (exact_mark, top3_mark) if x])
            print(
                f"    {status} {m['date']} | {m['teams']} | Predicted: {m['predicted']} | Actual: {m['actual']} {markers}"
            )
