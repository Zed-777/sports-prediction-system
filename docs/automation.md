# Automation Guide

This document describes the automated workflows and scripts that keep the
Sports Prediction System running on a scheduled basis.

---

## Overview

The system uses three layers of automation:

| Layer | Tool | Trigger |
|-------|------|---------|
| Daily data collection & result fetching | GitHub Actions | `0 3 * * *` (UTC) |
| Weekly accuracy optimization | GitHub Actions | `0 2 * * 1` (UTC) |
| Windows scheduled task (local / server) | PowerShell + Task Scheduler | Daily / weekly |

---

## GitHub Actions Workflows

All workflows are in `.github/workflows/`. Required GitHub secrets are listed
in `docs/SECRET_GUIDE.md`.

### `fetch-results.yml` — Daily result fetching & report regeneration

Runs at **03:00 UTC daily**.

Steps:
1. Collect new match results via `scripts/collect_historical_results.py`
2. **Update PredictionTracker** — `scripts/update_prediction_results.py`:
   queries the SQLite database (`data/predictions.db`) for pending predictions,
   looks up the final score via Football-Data.org, records the outcome, and
   updates Brier score & accuracy metrics.
3. Backfill provider IDs
4. Regenerate the last 5 match reports
5. Commits updated `data/historical/*.json` to `main`

To trigger manually:
```bash
gh workflow run fetch-results.yml
```

### `auto-optimize.yml` — Weekly accuracy optimization

Runs at **02:00 UTC every Monday**.

Runs `scripts/optimize_accuracy.py` and uploads optimization results as
workflow artifacts. No commits are made automatically — use
`scripts/commit_optimization_results.ps1` to selectively commit results.

### `ci.yml` / `ci-windows.yml` — Test suite

Runs on every push and PR. Full pytest suite on Ubuntu and Windows runners.
Integration tests are gated behind the `RUN_INTEGRATION_TESTS=true` env var
and the `run-integration` PR label.

### `synthetic-detection.yml` — Synthetic report audit

Runs weekly. Detects reports redirected to `reports/simulated/` (those that
failed the publication gate — see `config/settings.yaml`
`publication_gate` thresholds).

### `auto-merge-on-ready.yml` — Gated auto-merge

Merges PRs when:
- Label `ready-to-merge` is applied
- Labels `run-integration` **and** `legal-approved` are present
- All status checks are green

Uses `actions/github-script` to call the GitHub Merge API directly.

### `integration-tests-on-label.yml` — Integration tests on demand

Triggered by the `run-integration` label or manual dispatch. Requires API
keys stored in GitHub repository secrets.

---

## Windows Scheduled Tasks (local / server deployment)

Use the deploy scripts to register tasks on Windows:

```powershell
# Register daily + weekly tasks
.\deploy\register_fetch_scheduled_task.ps1

# Or use the combined deploy script
.\deploy\windows-deploy.ps1
```

Tasks log output to `data/logs/daily/`.

---

## Scripts Reference

### `scripts/update_prediction_results.py` — PredictionTracker result loop

Fetches actual match results for predictions stored in `data/predictions.db`
and updates accuracy metrics (Brier score, calibration).

```bash
# Default: process predictions for matches up to 7 days ago
python scripts/update_prediction_results.py

# Process 30 days back
python scripts/update_prediction_results.py --days-back 30

# Dry run (no DB writes)
python scripts/update_prediction_results.py --dry-run --verbose
```

Required env var: `FOOTBALL_DATA_API_KEY`

### `scripts/run_backtest.py` — Historical backtesting CLI (VB-001)

Runs time-series cross-validation backtesting using `app/models/backtesting.py`
against historical data in `data/historical/`.

```bash
# Backtest all leagues, 365 days of history
python scripts/run_backtest.py

# Specific leagues, custom windows
python scripts/run_backtest.py --leagues PL,PD --days 730 --train-window 180 --test-window 30

# Smoke test with dummy predictor (no API key needed)
python scripts/run_backtest.py --skip-predictor --verbose
```

Results are written to `reports/backtests/`.

### `scripts/commit_optimization_results.ps1` — Safe commit (TODO #4)

Stages `data/optimization_results/` and `reports/historical/` onto a new
branch and optionally pushes.

```powershell
# Commit only (no push)
.\scripts\commit_optimization_results.ps1

# Commit and push
$env:AUTO_PUSH = "true"
.\scripts\commit_optimization_results.ps1

# Custom branch and message
.\scripts\commit_optimization_results.ps1 -BranchName "opt/my-run" -CommitMsg "chore: optimization run 2026-03-02"
```

### `scripts/collect_historical_results.py` — Historical data collection

Fetches and backfills historical match results from Football-Data.org and
CSV fallbacks.

```bash
python scripts/collect_historical_results.py --fetch-all
python scripts/collect_historical_results.py --fetch-all --auto-optimize 50
```

### `scripts/optimize_accuracy.py` — Accuracy optimizer

Runs a parameter sweep to maximize prediction accuracy and writes results
to `data/optimization_results/`.

---

## Setting Up Secrets

See `docs/SECRET_GUIDE.md` for the full key list. Minimum required for
automated workflows:

| Secret | Used by |
|--------|---------|
| `FOOTBALL_DATA_API_KEY` | Result fetching, data collection |
| `API_FOOTBALL_KEY` | Injury data (optional) |
| `GITHUB_TOKEN` | Auto-merge, CI (auto-provided) |

To add secrets:
```bash
gh secret set FOOTBALL_DATA_API_KEY --body "your_key_here"
gh secret set API_FOOTBALL_KEY --body "your_key_here"
```

---

## Enabling GitHub Actions

If Actions are disabled on the repo:
```bash
gh api repos/Zed-777/sports-prediction-system --method PATCH \
  --field has_projects=true
```

Or via the repo Settings → Actions page.

---

## Local Developer Quick-Start

```powershell
# Activate venv
.\.venv\Scripts\Activate.ps1

# Run tests (excluding network-dependent tests)
$env:SKIP_INJURIES="1"
python -m pytest tests/ -p timeout --timeout=30 `
  --ignore=tests/test_flashscore_scraper.py `
  --ignore=tests/test_flashscore_debug.py `
  --ignore=tests/test_flashscore_decompression.py `
  --ignore=tests/test_flashscore_json_payload.py `
  --ignore=tests/test_flashscore_parser.py `
  --ignore=tests/test_flashscore_scraper_hardening.py `
  --ignore=tests/test_flashscore_fixture_parsing.py `
  --ignore=tests/test_integration_flashscore.py `
  --ignore=tests/test_generate_specific_match.py `
  -k "not flashscore" -q

# Generate a prediction report
python generate_fast_reports.py generate 1 matches for premier-league

# Run a backtest (smoke mode)
python scripts/run_backtest.py --skip-predictor

# Update prediction results manually
python scripts/update_prediction_results.py --dry-run
```
