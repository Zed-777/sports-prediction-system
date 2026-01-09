Results Fetcher & Optimization Workflow
=====================================

Overview
--------

This project now includes an automated "results fetcher" that:

- Collects prediction records from generated reports
- Fetches finished match results from Football-Data.org (preferred) or API-Football (fallback)
- Matches results to prediction records and updates `data/historical/{league}_results.json`
- Lets you compute accuracy and feed historical data into the optimizer

Quick commands
--------------

1. Collect latest predictions (from reports):

   ```powershell
   python scripts/collect_historical_results.py --league la-liga
   ```

2. Fetch finished match results and update historical file (last 7 days):

   ```powershell
   python scripts/collect_historical_results.py --fetch --league la-liga
   ```

   Or for all supported leagues:

   ```powershell
   python scripts/collect_historical_results.py --fetch-all
   ```

   Optional flags:
   - `--auto-optimize N` - After fetching, if the number of completed matches for a league >= N, the optimizer will run (e.g., `--auto-optimize 50`).
   - `--notify` - Send a notification email summary if SMTP env vars are configured (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `EMAIL_TO`).

3. Calculate accuracy for a league:

   ```powershell
   python scripts/collect_historical_results.py --accuracy la-liga
   ```

4. Run backtest / optimizer using historical data:

   ```powershell
   # quick simulated backtest
   python scripts/optimize_accuracy.py --mode backtest --league la-liga

   # parameter sweep
   python scripts/optimize_accuracy.py --mode experiment --param market_blend_weight --league la-liga

   # full optimization
   python scripts/optimize_accuracy.py --mode full-optimization --league la-liga
   ```

Scheduling Options
------------------

- Windows Task Scheduler (PowerShell example):

  ```powershell
  $Action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -Command 'cd C:\Path\To\STATS; python scripts/collect_historical_results.py --fetch-all'"
  $Trigger = New-ScheduledTaskTrigger -Daily -At 03:00AM
  Register-ScheduledTask -TaskName 'SportsForecastFetch' -Action $Action -Trigger $Trigger -Description 'Fetch results daily and update historical dataset'
  ```

- GitHub Actions (recommended for cloud-run): create `.github/workflows/fetch-results.yml` with a daily schedule that runs the script using project secrets (FOOTBALL_DATA_API_KEY or API_FOOTBALL_KEY).

Notes & Tips
------------

- Make sure `FOOTBALL_DATA_API_KEY` (or `API_FOOTBALL_KEY`) is set as an environment variable or in `.env` for the runner.
- The fetcher uses a case-insensitive match of home/away team and date to map API results to prediction records. If your team names differ, consider normalizing names in prediction JSONs.
- After accumulating a reasonable number of matched results (50+), run the optimizer and parameter sweeps to find improvements.
- You can disable external injury calls in generation runs by using `--no-injuries` to reduce rate-limiting during bulk runs.
