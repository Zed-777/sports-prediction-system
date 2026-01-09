# Scripts Directory

This folder contains helper scripts and automation utilities used by the SportsPredictionSystem.

Structure overview:

- `automation/` - PowerShell scripts for scheduled tasks and manual runners (`run_daily_job.ps1`, `run_weekly_optimization.ps1`).
- `helpers/` - Small helper scripts (aliases, convenience helpers).
- `collect_historical_results.py` - Collect predictions into `data/historical/` and update actual results.
- `optimize_accuracy.py` - Parameter sweep and optimization runner (generates results in `data/optimization_results/`).
- `setup_github_with_gh.ps1` - Optional helper to set repo secrets via `gh` (not required for local-only workflows).

Common commands:

```powershell
# Run daily collector
powershell -ExecutionPolicy Bypass -File scripts\automation\run_daily_job.ps1

# Run weekly optimizer
powershell -ExecutionPolicy Bypass -File scripts\automation\run_weekly_optimization.ps1

# Collect predictions for a single league
python scripts\collect_historical_results.py --league la-liga

# Run a full optimization
python scripts\optimize_accuracy.py --mode full --league la-liga
```

If you add a new script, add a short entry to this file describing its purpose and usage.