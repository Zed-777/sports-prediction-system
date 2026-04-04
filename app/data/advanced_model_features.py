"""Feature engineering utilities for the advanced model.

This module provides deterministic transforms to build a training dataset from
`data/historical/*_results.json`. It adds derived numeric features and a
stable encoding for categorical columns so CI can run smoke training reliably.
"""

import csv
import json
import random
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2]
HIST_DIR = BASE_DIR / "data" / "historical"
OUT_DIR = BASE_DIR / "data" / "processed" / "advanced_model"

# Basic columns kept for backward compatibility plus engineered features
OUT_COLUMNS = [
    "league",
    "league_idx",
    "home_team",
    "away_team",
    "expected_home_goals",
    "expected_away_goals",
    "goal_diff",
    "total_expected_goals",
    "home_win_prob",
    "draw_prob",
    "away_win_prob",
    "home_prob_ratio",
    "favored",
    "confidence",
    "target",
]


def _safe_get_prediction(entry: dict[str, Any]) -> dict[str, float]:
    pred = entry.get("prediction") or {}
    # support different naming variants
    hp = (
        pred.get("home_win_prob")
        or pred.get("home_win_probability")
        or pred.get("home_win")
        or 0.0
    )
    dp = (
        pred.get("draw_prob") or pred.get("draw_probability") or pred.get("draw") or 0.0
    )
    ap = (
        pred.get("away_win_prob")
        or pred.get("away_win_probability")
        or pred.get("away_win")
        or 0.0
    )
    # if probabilities are likely in 0..1 or in 0..100, normalize
    probs = [hp, dp, ap]
    probs = [float(x) for x in probs]
    if max(probs) > 1.1:
        # treat as percentages
        probs = [x / 100.0 for x in probs]
    s = sum(probs)
    if s <= 0:
        # fallback to uniform
        probs = [1 / 3, 1 / 3, 1 / 3]
    else:
        probs = [x / s for x in probs]
    conf = float(
        pred.get("confidence")
        or pred.get("report_accuracy_probability")
        or pred.get("data_quality_score")
        or 0.0,
    )
    # normalize confidence if in 0..100
    if conf > 1.1:
        conf = conf / 100.0

    return {
        "home_win_prob": probs[0],
        "draw_prob": probs[1],
        "away_win_prob": probs[2],
        "confidence": conf,
        "expected_home_goals": float(
            pred.get("expected_home_goals") or pred.get("expected_home") or 0.0,
        ),
        "expected_away_goals": float(
            pred.get("expected_away_goals") or pred.get("expected_away") or 0.0,
        ),
    }


def _extract_target(entry: dict[str, Any]) -> int:
    ar = entry.get("actual_result") or {}
    outcome = ar.get("outcome")
    if not outcome:
        # try to infer from scores
        hs = ar.get("home_score")
        as_ = ar.get("away_score")
        if hs is None or as_ is None:
            return -1
        if hs > as_:
            outcome = "home_win"
        elif hs == as_:
            outcome = "draw"
        else:
            outcome = "away_win"
    if outcome == "home_win":
        return 0
    if outcome == "draw":
        return 1
    if outcome == "away_win":
        return 2
    return -1


def _stable_league_index(all_leagues: list[str]) -> dict[str, int]:
    """Return a deterministic mapping from league name to integer index."""
    uniques = sorted(set(all_leagues))
    return {name: idx for idx, name in enumerate(uniques)}


def _engineer_features(pred: dict[str, float]) -> dict[str, float]:
    """Create simple deterministic engineered numeric features."""
    goal_diff = pred["expected_home_goals"] - pred["expected_away_goals"]
    total = pred["expected_home_goals"] + pred["expected_away_goals"]
    # ratio: home_win_prob relative to away_win_prob (stable and clipped)
    denom = max(pred["away_win_prob"], 1e-6)
    home_prob_ratio = pred["home_win_prob"] / denom
    # favored: 0=home,1=draw,2=away
    favored = int(
        max(
            range(3),
            key=lambda i: [
                pred["home_win_prob"],
                pred["draw_prob"],
                pred["away_win_prob"],
            ][i],
        ),
    )
    return {
        "goal_diff": round(goal_diff, 3),
        "total_expected_goals": round(total, 3),
        "home_prob_ratio": round(min(home_prob_ratio, 100.0), 3),
        "favored": int(favored),
    }


def build_sample_dataset(
    output_csv: Path, augment_per_match: int = 20, seed: int = None,
) -> None:
    """Build a small sample CSV with features and target.

    For each historical record in `data/historical`, produce `augment_per_match`
    augmented rows by jittering expected goals and probabilities slightly to
    produce a dataset suitable for quick smoke training runs.

    The `seed` parameter ensures deterministic output for unit tests and CI.
    """
    if seed is not None:
        random.seed(seed)

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    files = list(HIST_DIR.glob("*_results.json"))
    all_leagues: list[str] = []
    payloads: list[tuple[dict[str, Any], dict[str, float], int]] = []

    for f in files:
        try:
            entries = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for e in entries:
            pred = _safe_get_prediction(e)
            target = _extract_target(e)
            all_leagues.append(e.get("league", "") or "unknown")
            payloads.append((e, pred, target))

    league_map = _stable_league_index(all_leagues) if all_leagues else {"synthetic": 0}

    for e, pred, target in payloads:
        t = int(target)
        # if no actual outcome, sample target from probabilities deterministically
        if t == -1:
            r = random.random()
            if r < pred["home_win_prob"]:
                t = 0
            elif r < pred["home_win_prob"] + pred["draw_prob"]:
                t = 1
            else:
                t = 2
        for i in range(augment_per_match):
            # jitter expected goals and probabilities
            eh = max(0.0, pred["expected_home_goals"] + random.gauss(0, 0.2))
            ea = max(0.0, pred["expected_away_goals"] + random.gauss(0, 0.2))
            hp = max(0.001, min(0.999, pred["home_win_prob"] + random.gauss(0, 0.03)))
            dp = max(0.001, min(0.999, pred["draw_prob"] + random.gauss(0, 0.02)))
            ap = max(0.001, min(0.999, pred["away_win_prob"] + random.gauss(0, 0.03)))
            s = hp + dp + ap
            hp, dp, ap = hp / s, dp / s, ap / s
            conf = max(0.0, min(1.0, pred["confidence"] + random.gauss(0, 0.02)))

            engineered = _engineer_features(
                {
                    "expected_home_goals": eh,
                    "expected_away_goals": ea,
                    "home_win_prob": hp,
                    "draw_prob": dp,
                    "away_win_prob": ap,
                },
            )

            rows.append(
                {
                    "league": e.get("league", "") or "unknown",
                    "league_idx": league_map.get(e.get("league", "") or "unknown", 0),
                    "home_team": e.get("home_team", ""),
                    "away_team": e.get("away_team", ""),
                    "expected_home_goals": round(eh, 3),
                    "expected_away_goals": round(ea, 3),
                    "goal_diff": engineered["goal_diff"],
                    "total_expected_goals": engineered["total_expected_goals"],
                    "home_win_prob": round(hp, 4),
                    "draw_prob": round(dp, 4),
                    "away_win_prob": round(ap, 4),
                    "home_prob_ratio": engineered["home_prob_ratio"],
                    "favored": int(engineered["favored"]),
                    "confidence": round(conf, 4),
                    "target": int(t),
                },
            )

    # If no files or too few rows, synthesize small dataset to allow training to run
    if not rows:
        for i in range(200):
            eh = abs(random.gauss(1.5, 0.7))
            ea = abs(random.gauss(1.2, 0.7))
            hp = random.uniform(0.2, 0.6)
            dp = random.uniform(0.1, 0.35)
            ap = random.uniform(0.1, 0.6)
            s = hp + dp + ap
            hp, dp, ap = hp / s, dp / s, ap / s
            eng = _engineer_features(
                {
                    "expected_home_goals": eh,
                    "expected_away_goals": ea,
                    "home_win_prob": hp,
                    "draw_prob": dp,
                    "away_win_prob": ap,
                },
            )
            rows.append(
                {
                    "league": "synthetic",
                    "league_idx": 0,
                    "home_team": "A",
                    "away_team": "B",
                    "expected_home_goals": round(eh, 3),
                    "expected_away_goals": round(ea, 3),
                    "goal_diff": eng["goal_diff"],
                    "total_expected_goals": eng["total_expected_goals"],
                    "home_win_prob": round(hp, 4),
                    "draw_prob": round(dp, 4),
                    "away_win_prob": round(ap, 4),
                    "home_prob_ratio": eng["home_prob_ratio"],
                    "favored": int(eng["favored"]),
                    "confidence": round(random.uniform(0.4, 0.95), 4),
                    "target": random.choice([0, 1, 2]),
                },
            )

    # Write CSV
    with output_csv.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=OUT_COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in OUT_COLUMNS})

    print(f"Wrote {len(rows)} rows to {output_csv}")


if __name__ == "__main__":
    from argparse import ArgumentParser

    p = ArgumentParser()
    p.add_argument("--out", default=OUT_DIR / "sample_train.csv")
    p.add_argument("--augment", type=int, default=20)
    p.add_argument("--seed", type=int, default=None)
    args = p.parse_args()
    build_sample_dataset(
        Path(args.out), augment_per_match=int(args.augment), seed=args.seed,
    )
