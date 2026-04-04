"""Evaluate an advanced model artifact against historical results.

Computes log_loss, multiclass Brier score, accuracy, and a simple calibration
summary (per-class binned calibration). Outputs JSON to `--out` path.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import log_loss

from app.data.advanced_model_features import _extract_target
from app.models.advanced_predictor import AdvancedAIMLPredictor


def multiclass_brier(y_true: list[int], y_prob: list[list[float]]) -> float:
    # y_prob: n x k
    n = len(y_true)
    if n == 0:
        return float("nan")
    k = len(y_prob[0])
    s = 0.0
    for yi, pi in zip(y_true, y_prob):
        onehot = np.zeros(k, dtype=float)
        onehot[yi] = 1.0
        p = np.array(pi, dtype=float)
        s += float(((p - onehot) ** 2).sum())
    return s / n


def calibration_summary(y_true: list[int], y_prob: list[list[float]], bins: int = 10):
    # For each class, create bins and compute mean predicted vs observed
    n = len(y_true)
    if n == 0:
        return {}
    k = len(y_prob[0])
    res = {}
    y_prob = np.array(y_prob)
    y_true = np.array(y_true)
    for cls in range(k):
        probs = y_prob[:, cls]
        # bin edges
        bin_edges = np.linspace(0.0, 1.0, bins + 1)
        cls_res = []
        for i in range(bins):
            lo, hi = bin_edges[i], bin_edges[i + 1]
            mask = (
                (probs >= lo) & (probs < hi)
                if i < bins - 1
                else (probs >= lo) & (probs <= hi)
            )
            if mask.sum() == 0:
                continue
            mean_pred = float(probs[mask].mean())
            observed = float((y_true[mask] == cls).mean())
            cls_res.append(
                {
                    "bin": i,
                    "predicted_mean": mean_pred,
                    "observed_freq": observed,
                    "count": int(mask.sum()),
                },
            )
        res[f"class_{cls}"] = cls_res
    return res


def evaluate(model_path: Path, historical_dir: Path, bins: int = 10):
    predictor = AdvancedAIMLPredictor(model_path)

    y_true = []
    y_prob = []

    files = list(historical_dir.glob("*_results.json"))
    for f in files:
        try:
            entries = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for e in entries:
            t = _extract_target(e)
            if t == -1:
                continue
            # build match info from prediction dict
            match_pred = e.get("prediction") or {}
            features = predictor.extract_advanced_features(match_pred)
            pred = predictor.predict_with_ml_ensemble(features)
            probs = [pred["home_win_prob"], pred["draw_prob"], pred["away_win_prob"]]
            # ensure well-formed
            s = sum(probs)
            if s <= 0:
                continue
            probs = [float(p) / s for p in probs]
            y_true.append(int(t))
            y_prob.append(probs)

    if not y_true:
        raise RuntimeError("No finished matches found in historical directory")

    accuracy = float(np.mean([int(np.argmax(p) == t) for p, t in zip(y_prob, y_true)]))
    ll = float(log_loss(y_true, y_prob, labels=[0, 1, 2]))
    brier = float(multiclass_brier(y_true, y_prob))
    calib = calibration_summary(y_true, y_prob, bins=bins)

    out = {
        "model": str(model_path),
        "n_matches": len(y_true),
        "accuracy": accuracy,
        "log_loss": ll,
        "brier_score": brier,
        "calibration": calib,
    }
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument(
        "--historical",
        default=Path(__file__).resolve().parents[1] / "data" / "historical",
    )
    p.add_argument("--out", default=None)
    p.add_argument("--bins", type=int, default=10)
    args = p.parse_args()

    model_path = Path(args.model)
    historical_dir = Path(args.historical)
    out = (
        Path(args.out)
        if args.out
        else model_path.with_name(model_path.stem + "_eval.json")
    )

    res = evaluate(model_path, historical_dir, bins=args.bins)
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"Wrote evaluation to {out}")


if __name__ == "__main__":
    main()
