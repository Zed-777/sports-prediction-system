"""Training script for Advanced Model (baseline LightGBM)

This script is a scaffold for development. It includes a CLI and basic deterministic behavior.
Usage (local dev):
  python scripts/train_advanced_model.py --input data/processed/advanced_model/train.csv --outdir models/advanced --seed 42
"""

import argparse
from pathlib import Path
import json
import os
import sys

# Make repo root importable for local runs
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import numpy as np

try:
    import lightgbm as lgb
except Exception:
    lgb = None

# Fallback to scikit-learn RandomForest if LightGBM is not available
try:
    from sklearn.ensemble import RandomForestClassifier
except Exception:
    RandomForestClassifier = None


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--input", type=str, default="data/processed/advanced_model/train.csv"
    )
    p.add_argument("--outdir", type=str, default="models/advanced")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def train_baseline(train_path: Path, outdir: Path, seed: int = 42):
    # Minimal behavior: load CSV with columns: features..., target
    if not train_path.exists():
        raise FileNotFoundError(
            f"Training data not found at {train_path}. Create processed features first."
        )

    df = pd.read_csv(train_path)
    if "target" not in df.columns:
        raise ValueError("Expected column `target` in training CSV")

    # Use only numeric features for baseline training; leave categorical encoding for later
    y = df["target"]
    X = df.select_dtypes(include=["number"])
    if "target" in X.columns:
        X = X.drop(columns=["target"])
    if X.shape[1] == 0:
        raise ValueError(
            "No numeric features found for training. Ensure feature pipeline produces numeric columns."
        )

    # quick deterministic split
    rng = np.random.RandomState(seed)
    idx = np.arange(len(df))
    rng.shuffle(idx)
    split = int(0.8 * len(df))
    train_idx, val_idx = idx[:split], idx[split:]

    # If LightGBM available, use it; otherwise fallback to RandomForestClassifier
    if lgb is not None:
        dtrain = lgb.Dataset(X.iloc[train_idx], label=y.iloc[train_idx])
        dval = lgb.Dataset(X.iloc[val_idx], label=y.iloc[val_idx])

        params = {
            "objective": "multiclass",
            "num_class": 3,
            "metric": "multi_logloss",
            "verbosity": -1,
            "seed": seed,
        }

        try:
            model = lgb.train(
                params,
                dtrain,
                valid_sets=[dval],
                num_boost_round=100,
                early_stopping_rounds=10,
            )
        except TypeError:
            # Older LightGBM versions may not support the keyword argument
            # Use callbacks-based API where available
            try:
                model = lgb.train(
                    params,
                    dtrain,
                    valid_sets=[dval],
                    num_boost_round=100,
                    callbacks=[lgb.early_stopping(10)],
                )
            except Exception:
                # Fallback to plain training without early stopping
                model = lgb.train(
                    params,
                    dtrain,
                    valid_sets=[dval],
                    num_boost_round=100,
                )

        outdir.mkdir(parents=True, exist_ok=True)
        model_path = outdir / f"lightgbm_baseline_{seed}.txt"
        model.save_model(str(model_path))

        # metrics: compute validation logloss
        preds = model.predict(X.iloc[val_idx])
        # Save a small metrics JSON
        metrics = {
            "val_loss": float(
                np.mean(
                    -np.log(
                        np.maximum(
                            1e-15,
                            preds[
                                np.arange(len(preds)),
                                y.iloc[val_idx].astype(int).to_numpy(),
                            ],
                        )
                    )
                )
            )
        }
        with open(outdir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        # write a simple manifest for model registry
        manifest = {
            "artifact": str(model_path),
            "framework": "lightgbm",
            "seed": seed,
            "input": str(train_path),
            "metrics": metrics,
        }
        with open(outdir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        print("Saved model to:", model_path)
        print("Metrics:", metrics)
        return model_path, metrics
    else:
        if RandomForestClassifier is None:
            raise RuntimeError(
                "Neither lightgbm nor scikit-learn RandomForest are available in this environment"
            )

        # Train a simple RandomForest as fallback
        clf = RandomForestClassifier(n_estimators=100, random_state=seed)
        clf.fit(X.iloc[train_idx], y.iloc[train_idx])
        preds = clf.predict_proba(X.iloc[val_idx])

        outdir.mkdir(parents=True, exist_ok=True)
        import joblib

        model_path = outdir / f"rf_baseline_{seed}.joblib"
        joblib.dump(clf, model_path)

        # metrics: log loss (robust to tiny validation sets)
        from sklearn.metrics import log_loss

        try:
            val_loss = float(log_loss(y.iloc[val_idx], preds))
        except Exception:
            # In very small validation sets log_loss may fail if only one class present
            val_loss = None
        metrics = {"val_loss": val_loss}
        with open(outdir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        manifest = {
            "artifact": str(model_path),
            "framework": "sklearn",
            "seed": seed,
            "input": str(train_path),
            "metrics": metrics,
        }
        with open(outdir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        print("Saved RF model to:", model_path)
        print("Metrics:", metrics)
        return model_path, metrics


if __name__ == "__main__":
    args = parse_args()
    train_path = Path(args.input)
    outdir = Path(args.outdir)
    train_baseline(train_path, outdir, args.seed)
