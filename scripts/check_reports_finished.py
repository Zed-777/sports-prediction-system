#!/usr/bin/env python3
"""
Check reports directory for finished matches and summarize correctness

Usage:
    python scripts/check_reports_finished.py
"""

import json
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports" / "leagues"
HIST_DIR = PROJECT_ROOT / "data" / "historical"


def parse_match_datetime(pred):
    # Accept 'match_date' ISO or 'date' + 'time'
    match_date = pred.get("match_date") or None
    if not match_date:
        d = pred.get("date")
        t = pred.get("time")
        if d and t:
            match_date = f"{d}T{t}"
        elif d:
            match_date = d
    if not match_date:
        return None
    try:
        return datetime.fromisoformat(match_date.replace("Z", "+00:00"))
    except Exception:
        try:
            # Try common format
            return datetime.strptime(match_date, "%Y-%m-%dT%H:%M")
        except Exception:
            try:
                return datetime.strptime(match_date, "%Y-%m-%d")
            except Exception:
                return None


def load_historical_for_league(league):
    path = HIST_DIR / f"{league}_results.json"
    if not path.exists():
        return {}
    try:
        data = json.load(open(path, "r", encoding="utf-8"))
    except Exception:
        return {}
    return {r.get("match_id"): r for r in data}


def main():
    now = datetime.now(timezone.utc)
    leagues = [p for p in REPORTS_DIR.iterdir() if p.is_dir()]
    summary = {}
    missing_results = []

    for league_dir in leagues:
        league = league_dir.name
        hist = load_historical_for_league(league)
        finished_total = 0
        recorded_results = 0
        outcome_correct = 0
        exact_correct = 0
        top3_correct = 0
        details = []

        matches_dir = league_dir / "matches"
        if not matches_dir.exists():
            summary[league] = (0, 0, 0, 0, 0)
            continue
        for match_dir in matches_dir.iterdir():
            if not match_dir.is_dir():
                continue
            pred_file = match_dir / "prediction.json"
            if not pred_file.exists():
                continue
            try:
                pred = json.load(open(pred_file, "r", encoding="utf-8"))
            except Exception:
                continue
            mdt = parse_match_datetime(pred)
            finished = False
            if mdt:
                # convert naive to UTC if no tzinfo
                if mdt.tzinfo is None:
                    # treat as local naive; compare by local time
                    finished = mdt <= datetime.now()
                else:
                    finished = mdt <= now
            else:
                # if no date, skip
                continue

            if not finished:
                continue

            finished_total += 1
            mid = match_dir.name
            record = hist.get(mid)
            if not record:
                missing_results.append((league, mid))
                details.append(
                    (
                        mid,
                        pred.get("home_team"),
                        pred.get("away_team"),
                        "no_result",
                        None,
                        None,
                    )
                )
                continue
            ar = record.get("actual_result")
            if not ar:
                missing_results.append((league, mid))
                details.append(
                    (
                        mid,
                        pred.get("home_team"),
                        pred.get("away_team"),
                        "no_result",
                        None,
                        None,
                    )
                )
                continue
            recorded_results += 1
            pred_corr = bool(record.get("prediction_correct", False))
            exact_corr = bool(record.get("exact_score_correct", False))
            top3 = bool(record.get("score_in_top3", False))
            if pred_corr:
                outcome_correct += 1
            if exact_corr:
                exact_correct += 1
            if top3:
                top3_correct += 1
            details.append(
                (
                    mid,
                    pred.get("home_team"),
                    pred.get("away_team"),
                    "recorded",
                    pred_corr,
                    exact_corr,
                )
            )

        summary[league] = {
            "finished_total": finished_total,
            "recorded_results": recorded_results,
            "outcome_correct": outcome_correct,
            "exact_correct": exact_correct,
            "top3_correct": top3_correct,
            "details": details,
        }

    # Print summary
    print("Finished matches & correctness summary:")
    print("=======================================\n")
    for league, stats in summary.items():
        print(f"League: {league}")
        print(f"  Finished matches: {stats['finished_total']}")
        print(f"  Recorded results: {stats['recorded_results']}")
        print(f"  Outcome correct: {stats['outcome_correct']}")
        print(f"  Exact score correct: {stats['exact_correct']}")
        print(f"  Score in top-3: {stats['top3_correct']}\n")

    if missing_results:
        print("\nFinished matches missing results in historical DB:")
        for league, mid in missing_results:
            print(f"  {league}: {mid}")


if __name__ == "__main__":
    main()
