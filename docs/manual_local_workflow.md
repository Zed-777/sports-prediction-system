# Manual Local Workflow (No Cloud Automation)

This document describes the manual, local-only workflow for running the SportsPredictionSystem, collecting predictions, and optimizing accuracy without using any cloud services or GitHub Actions. Follow the steps carefully and keep secrets in your local `.env` file (do NOT commit `.env`).

## Quick Checklist

- [ ] Activate Python virtual environment
- [ ] Install required Python packages
- [ ] Populate `.env` with API keys (see template)
- [ ] Generate predictions before matchday
- [ ] Collect predictions into `data/historical/`
- [ ] After matches, update actual results
- [ ] Run optimizer when you have enough completed matches (recommended 50+)

---

## Environment Setup (one-time)

1. Activate your venv

```powershell
& .\.venv\Scripts\Activate.ps1
```

1. Install Python dependencies

```powershell
python -m pip install -r requirements.txt
```

1. Copy and edit `.env`

- Copy `.env.example` or the provided `.env` template and fill in real API keys.
- Required keys (examples): `FOOTBALL_DATA_API_KEY`, `API_FOOTBALL_KEY`, `ODDS_API_KEY`, `SECRET_KEY`, `DATABASE_URL`.
- **Important:** Do NOT commit `.env` to source control.

1. Verify basic tools

```powershell
python --version
python -m pytest -q  # run tests (some network tests are skipped)
```

---

## Daily Manual Routine (before matchday)

1. Generate predictions (example):

```powershell
python generate_fast_reports.py generate 5 matches for la-liga
```

1. Collect predictions into the historical database:

```powershell
python scripts/collect_historical_results.py --league la-liga
# or to collect all leagues
python scripts/collect_historical_results.py --all-leagues
```

1. Check logs (for the collector):

```powershell
Get-ChildItem data\logs\daily_job_*.log | Sort-Object LastWriteTime -Descending
Get-Content data\logs\daily_job_YYYYMMDD_HHMMSS.log -Tail 200
```

---

## After Matches (manual update)

1. Update actual result for a match (example):

```powershell
python scripts/collect_historical_results.py --update-result la-liga rayo-vallecano-de-madrid_vs_real-betis-balompi_2025-12-15 2 1
```

1. Recalculate accuracy metrics:

```powershell
python scripts/collect_historical_results.py --accuracy la-liga
```

Notes:

- The `match_id` is the directory name under `reports/leagues/{league}/matches/`.

---

## Weekly Manual Routine (run when you have enough data)

1. Run the optimizer (recommended after 50+ completed matches):

```powershell
python scripts/optimize_accuracy.py --mode full --league la-liga
```

1. Review results in `data/optimization_results/`.

2. If you want to apply recommended parameter changes, edit the config files indicated in the optimization output and re-run a targeted sweep for validation.

---

## Helpful Scripts

- `scripts/collect_historical_results.py` - Collects predictions and updates historical DB
- `scripts/optimize_accuracy.py` - Parameter sweeps and optimization runner
- `scripts/automation/run_daily_job.ps1` - Manual daily runner (collects predictions)
- `scripts/automation/run_weekly_optimization.ps1` - Manual weekly optimizer runner
- `scripts/setup_github_with_gh.ps1` - (Optional) helper for GitHub; not required for local-only

---

## Troubleshooting

- No historical records found: ensure `reports/leagues/{league}/matches/` contains prediction folders and run collector.
- Collector errors: inspect `data/logs/daily_job_*.log` for full stdout/stderr.
- Optimizer reports "no historical data": run ``collect_historical_results.py`` and ensure you have completed matches with `actual_result` filled.

---

## Optional: Local Automation (Windows Scheduled Tasks)

If, in the future, you decide to schedule local tasks (Windows Scheduled Tasks) rather than run them manually, see `scripts/automation/register_scheduled_tasks.ps1`. This file will create two scheduled tasks:

- `SPS_DailyCollection` - runs `run_daily_job.ps1` daily
- `SPS_WeeklyOptimization` - runs `run_weekly_optimization.ps1` weekly

> These tasks require admin privileges to register. We recommended continuing with manual runs for full control.

---

## Where to find things in the repo explorer

- Configuration & settings: `config/settings.yaml` and `config/accuracy_optimization_workflow.json`
- Data folders: `data/historical/`, `data/optimization_results/`, `data/logs/`
- Scripts: `scripts/collect_historical_results.py`, `scripts/optimize_accuracy.py`, `scripts/automation/`
- Docs: `docs/manual_local_workflow.md` (this file)

---

If you'd like, I can also add a one-line PowerShell alias file to quickly run daily/weekly commands (dot-sourceable) — let me know and I will add it under `scripts/helpers/`.
