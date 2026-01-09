# Advanced Model Plan — Phase 1 (Design + Baseline)

**Author:** Automated design scaffolding
**Date:** 2025-12-23

## Goals

- Build a robust, reproducible ML model that improves prediction accuracy for match outcomes and expected goals.
- Provide well-tested training, evaluation, and deployment artifacts so production can use the model defensibly.
- Ensure model quality with reproducible backtesting and monitoring; allow safe rollouts.

## Success criteria (acceptance)

- Model improves baseline accuracy (e.g., +X% absolute improvement as measured against historical holdout and A/B tests) or shows superior Brier/LogLoss and calibration.
- Training pipeline, artifact, & evaluation saved under `models/advanced/` and the artifact loads cleanly in `app/models/advanced_predictor.py`.
- Contract tests pass (no NaNs, probabilities sum to 1, ranges valid) and CI runs a smoke inference.

## Data sources

- Primary: historical predictions + actual results in `data/historical/` and `data/processed/`.
- Supplementary: feature sources from `app/data/*` (xG, H2H, form, weather, referee, team news, odds when available).

## Feature engineering plan

- Time-windowed form features (last 3/5/10 matches): goals for/against, xG, points per match
- Team strength features: ELO or aggregated ELO-like metric
- Head-2-head features: H2H last 5 matches
- Match context: home/away, days rest, weather, referee, market odds (if available)
- Categorical encodings: team IDs -> embeddings or one-hot if small cardinality
- Missing handling: explicit flags for missingness

## Model architecture candidates

- Tree-based gradient boosting (LightGBM / CatBoost) as baseline for tabular data
- Ensemble of probabilistic models (Poisson/Deep Poisson + boosted trees) as next step
- Optionally a calibrated probability layer using isotonic or Platt scaling

## Training & validation protocol

- Use time-based CV (rolling-origin) for backtesting to respect temporal ordering
- Hold out last N months as final test to measure expected production performance
- Track metrics: Accuracy (top-win/draw/away), Brier score, LogLoss, calibration curves, AUC for binary subtasks

## Model artifact & reproducibility

- Save models to `models/advanced/<model_name>_<YYYYMMDD>_<version>.pkl` (or .bin for CatBoost/LightGBM)
- Save metadata JSON (hyperparams, seed, dataset hash, metric results)
- Add reproducible training script `scripts/train_advanced_model.py` with fixed seed and deterministic config

## Evaluation & A/B testing

- Provide `scripts/evaluate_model.py` to compute backtest metrics and A/B comparisons vs current production baseline
- Add a small A/B harness to simulate head-to-head across historical records

## CI & gating

- Add contract tests for outputs and add a CI job to run training smoke (small sample) + inference contract tests
- Nightly scheduled evaluation to re-run backtests on rolling window

## Monitoring & deployment

- Instrument inference to log model version and confidence metrics per prediction
- Implement drift detector (feature drift + target drift) and trigger re-evaluation when thresholds exceed

## Roadmap (implementation phases)

1. Design & features (this doc + prototype features) — 2 days
2. Baseline training script & local artifact (LightGBM) — 3–5 days
3. Backtesting & evaluation harness — 2–3 days
4. Integration into predictor pipeline + contract tests — 2–3 days
5. CI, artifact registry, scheduled evaluation — 3–5 days
6. Maturation: ensembles, calibration, monitoring — ongoing

## Notes / Risks

- Requires adequate historical labeled data (finished matches) for robust backtesting; recommend minimum 1–2 seasons per league for statistically meaningful results.
- Some external features (odds, injuries) need keys/availability and can affect reproducibility; provide toggles when missing.

## Next immediate step

- Implement data feature pipeline prototypes and add a small reproducible training script that trains a LightGBM on a small sample and writes an artifact and metrics JSON.
