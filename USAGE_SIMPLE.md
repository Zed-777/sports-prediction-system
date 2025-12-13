# Sports Prediction System — Simple Usage Guide

This guide explains how to use, train, and run predictions with the SportsPredictionSystem in simple terms. It is written for people who are not experts.

## Quick Overview

- The system ingests match data, trains machine learning models, and produces match predictions and reports.
- Reports are saved to `reports/` and models are saved to `models/ml_enhanced/`.
- If the system doesn't have enough real historical data, it will use a fallback (simulated) training dataset so it still runs.

---

## 1) Setup (Windows PowerShell)

1. Open PowerShell in the project folder.
2. Create and activate a virtual environment (if you haven't already):

```powershell
python -m venv .venv-Z1.1
.\.venv-Z1.1\Scripts\Activate.ps1
# Install dependencies
pip install -r requirements.txt
```

> Tip: If you already use `.venv-Z1.1`, the workspace is configured to pick it up.

---

## 2) Collect Historical Data (so models can learn)

If you have copied CSV files to `data/backup_csv/` (e.g., `la_liga_matches.csv`), run:

```powershell
python scripts/collect_historical_data.py
```

This will:

- Read CSV files, compute simple features (like recent form, head-to-head stats), and save them into `data/processed/historical/historical_dataset.json`.

Optional: If you have a Football-Data.org API key, set the environment variable and re-run to fetch more data via API.

```powershell
$env:FOOTBALL_DATA_API_KEY = "YOUR_API_KEY_HERE"
python scripts/collect_historical_data.py
```

### What do we mean by placeholders

Placeholders are example values that live in `env.example` or `env.example` files and contain no real key material. Example:

```bash
FOOTBALL_DATA_API_KEY=YOUR_FOOTBALL_DATA_V4_API_KEY
```

This signals to developers what keys are required, but **no real keys should be committed** to the repository.

Use one of the secure key storage approaches below:

- Local dev: Keep a real `.env` **locally** (copy `.env.example` to `.env` before running). Do *not* commit `.env`.
- CI / Scheduled fetch: store keys as GitHub Secrets (recommended), then reference them from workflows.
- Production: rotate keys using a secret manager (Azure Key Vault / AWS Secrets Manager) and mount secrets to the environment.

---

## 10) API Keys the system uses (and how to set them)

Required keys and reasons:

- `FOOTBALL_DATA_API_KEY` — Football-Data.org v4 (match details and historical data).
- `API_FOOTBALL_KEY` — API-Football (RapidAPI) alternative data source (fixtures, extras).
- `SPORTSDATA_API_KEY` — SportsData.io (commercial) – optional.
- `SPORTSRADAR_API_KEY` — optional (data feeds, advanced stats).
- `ODDS_API_KEY` — odds providers for market data.
- `OPENMETEO_API_KEY` — optional weather data.

How to set keys (PowerShell):

```powershell
# Set for current session
$env:FOOTBALL_DATA_API_KEY = 'YOUR_KEY'
$env:API_FOOTBALL_KEY = 'YOUR_RAPIDAPI_KEY'

# For the whole session: place in a `.env` file and run the local venv activate script
```

How to set keys in GitHub Actions (recommended for scheduled fetch): set them under repo `Settings > Secrets` as `FOOTBALL_DATA_API_KEY`, `API_FOOTBALL_KEY`, etc., then in the workflow call the fetch script using those secrets.

---

## 11) Rotating and revoking keys

- If a key was committed to the repo by mistake, rotate it immediately through the provider console and remove it from the repository.
- Use `scripts/secure_env_keys.py` to automatically back up and clear the `.env` file in this repository.
- Keep the backup `.env.backup` outside the repository or in a securely managed store (not committed to git).

### Quick key status summary (what we found when inspecting repository)

- `FOOTBALL_DATA_API_KEY`: Present in `.env.backup` and validated with Football-Data.org v4 (200 OK) — your key works for some endpoints.
- `API_FOOTBALL_KEY`: Not set or placeholder — not available; set this to pull extra data from API-Football.
- `ODDS_API_KEY`: Present in `.env.backup` but we didn't validate the provider with a live query.
- Other optional keys (BallDontLie, SportsData.io, SportsRadar, OpenMeteo) are placeholders.

If you want, run `python scripts/list_api_keys_status.py` to see a live detection of which keys are present, placeholders, and whether the Football-Data.org key validates.

The script tries to read CSVs, and if the API key is set, it will fetch additional matches.

Optional: If you have API-Football (RapidAPI) credentials, set this env var too to fetch additional fixtures and historic seasons:

```powershell
$env:API_FOOTBALL_KEY = "YOUR_API_FOOTBALL_RAPIDAPI_KEY"
$env:API_FOOTBALL_LEAGUES = "140"  # comma-separated league ids if you want more than one (e.g. "39,140")
python scripts/collect_historical_data.py
```

Tip: Control which seasons to collect using `COLLECT_SEASONS` environment variable. For example:

```powershell
$env:COLLECT_SEASONS = "2019,2020,2021,2022,2023,2024"
python scripts/collect_historical_data.py
```

Alternatively you can use the new dedicated fetch script which writes CSVs directly into `data/backup_csv/`:

```powershell
$env:FOOTBALL_DATA_API_KEY = "YOUR_API_KEY_HERE"
python scripts/fetch_historical_api.py --competition PD --start 2018 --end 2023
```

This will create files like `data/backup_csv/pd_2018_api.csv` which `scripts/collect_historical_data.py` will ingest on the next run.

---

## 3) Train Models

There are two ways to train depending on your data availability:

A) Quick synthetic training (bootstrap models) — used if you don't have historical data:

```powershell
python scripts/train_initial_models.py

This trains the models on a small synthetic dataset to get the system up and running, and it writes models to `models/ml_enhanced/`.

B) Train from processed historical dataset (recommended if you have enough data):

```powershell
python scripts/train_models.py
```

This will:

- Load `data/processed/historical/historical_dataset.json` (created by the collector script).
- Train the ML ensemble and save results to `models/ml_enhanced/`.

Note: If the processed dataset has fewer than ~50 matches, the trainer will fall back to synthetic data and warn you.

---

## 4) Generate Predictions and Reports

Once you have trained models (or are running with synthetic models), generate reports with:

```powershell
python generate_fast_reports.py generate 1 matches for la-liga
```

Or run the Phase 2 Lite predictor directly for a single prediction (smoke test):

```powershell
python phase2_lite.py
```

Output files are saved to `reports/leagues/<league>/matches/<match-slug>/prediction.json`.

The JSON contains: probabilities, confidence, confidence intervals, reliability metrics, and model details.

---

## 5) Check Model Files

- Models are in `models/ml_enhanced/` (e.g., `random_forest.pkl`, `gradient_boosting.pkl`, `xgboost.pkl`, `lightgbm.pkl`, `scaler.pkl`).
- If models are not found, either your training step did not complete or something wrote them in a different path. Run the trainer again.

---

## 6) Testing and Sanity Checks

Run the unit tests:

```powershell
python -m pytest -q
```

Check the tests for loader and prediction integrity: `tests/test_historical_loader.py` and other tests help validate the system.

---

## 7) Troubleshooting (Common Problems)

- "No models loaded" — Check `models/ml_enhanced/` and rerun training.
- "Insufficient training data" — Add more CSVs to `data/backup_csv` or use the API to collect more historical matches.
- "Fallback predictions" — The fallback is used when models are not trained or dependencies missing (e.g., XGBoost/LightGBM/TF). Train models and ensure dependencies are installed.
- "API errors" — Set the `FOOTBALL_DATA_API_KEY` environment variable correctly and check network connectivity.
- "Reports have low reliability" — This happens when data quality is low (e.g., missing H2H, referee info, or incomplete team news). Gather more data to improve quality.

---

## 8) Want to Improve Accuracy?

- Collect more historical match data (more seasons and leagues).
- Add richer features (use the legacy 48-feature extractor in the `legacy_files` and port to `app/models/feature_extractor.py`).
- Use cross-validation and hyperparameter tuning in `app/models/ml_enhancer.py`.
- Add model monitoring: accuracy/precision, drift detection, and model versioning.

---

## 9) Where to find stuff (short cheat sheet)

- Data: `data/backup_csv/`, `data/processed/historical/`
- Trained Models: `models/ml_enhanced/`
- Reports: `reports/leagues/<league>/matches/<match>/`
- Scripts: `scripts/` folder
- Core logic: `app/models/advanced_ai_engine.py`, `app/models/ml_enhancer.py`
- Collect data: `scripts/collect_historical_data.py`
- Train models: `scripts/train_models.py` and `scripts/train_initial_models.py`

---

If you'd like, I can:

- Add a simple GUI wrapper to run these steps.
- Add a small script to loop historical API calls and populate `data/backup_csv/`.
- Add a short checklist to the README for non-technical users.

---

## API Cost & Tier Summary (quick guide)

This system uses several providers; here are quick notes on whether they're free or commercial.

- Football-Data.org (v4): Free tier available with limited endpoints (rate-limited). Some historical and team-detail endpoints are behind paid plans.
- API-Football (RapidAPI): Free tier exists with limited monthly calls; paid tiers increase limits and features.
- SportsData.io: Commercial, paid access required for most data.
- SportRadar: Commercial, paid access only for historical and advanced feeds.
- Odds APIs: Various providers; many provide limited free tiers, but larger access is paid.
- Open-Meteo: Free API with generous limits for weather data.

If you are on a free tier (especially Football-Data.org or API-Football), monitor for 403/429 responses — the fetcher supports logging and fallback to alternate APIs when possible.

### Using the API-Football fetcher

We added `scripts/fetch_api_football.py` which uses RapidAPI's API-Football (v3) interface. You can fetch directly into `data/backup_csv/`:

```powershell
$env:API_FOOTBALL_KEY = "YOUR_API_FOOTBALL_RAPIDAPI_KEY"
python scripts/fetch_api_football.py --leagues 140 --seasons 2018,2019,2020 --outfile data/backup_csv/api_football_140_2018_2020.csv
```

The `collect_historical_data.py` script will detect `API_FOOTBALL_KEY`, `API_FOOTBALL_LEAGUE` and `API_FOOTBALL_SEASONS` environment variables and call this fetcher for you; setting a single line is sufficient:

```powershell
$env:API_FOOTBALL_KEY = 'your_rapidapi_key'
$env:API_FOOTBALL_LEAGUE = '140'
$env:API_FOOTBALL_SEASONS = '2018,2019,2020'
python scripts/collect_historical_data.py
```

---

## 10) Automate the fetch -> ingest -> train workflow

We added `scripts/auto_update_and_train.ps1` to orchestrate the whole flow. Example:

```powershell
# Backfill seasons once
.\scripts\auto_update_and_train.ps1 -Competition PD -Start 2014 -End 2023

# Run daily for new matches (without backfill)
.\scripts\auto_update_and_train.ps1 -Competition PD -Start 2024 -End 2024
```

Scheduling options:

- Windows Task Scheduler: Create a task that runs the above command daily/weekly. It's reliable and works on the machine running the app.
- GitHub Actions: Use a scheduled workflow to run the script using a runner (if you want centralized, cloud-based updates and to avoid using your workstation). Keep API keys in GitHub Secrets.
- Linux/cron: If running on Linux, a cron job can call the same steps.

When to run:

- Backfill (initial): Run once with many seasons (2010–2024) — the script is tolerant but consider API rate limits.
- Incremental (ongoing): Run once per day on off-peak hours. For major leagues, daily is fine, weekly is safe if you want to avoid frequent re-training.
- Train cadence: Retrain weekly or after every X new matches (e.g., 100 new finished matches) — if you track model degradation, retrain earlier when performance drops.
