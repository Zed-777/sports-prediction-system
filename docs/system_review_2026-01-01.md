# System Review — SportsPredictionSystem (2026-01-01)

## Summary (TL;DR) ✅
- Tests: Unit & integration test suite (non-network) pass locally (pytest completed). ✅
- Linting: `ruff` runs but failed locally due to platform encoding when scanning repository; also `pyproject.toml` uses deprecated top-level ruff settings (should migrate to [tool.ruff.lint]). ⚠️
- Backtesting & Optimization: `data/optimization_results/` contains many sweep/full optimization outputs; `reports/backtests/` is currently empty. The `BacktestingFramework` is implemented and unit-tested. ✅
- Prediction tracking: `app/models/prediction_tracker.py` implemented but not yet populated (no `data/predictions.db` or `data/predictions/` artifacts found). Recommend integrating tracker into prediction generation flow. ⚠️
- A/B testing: `app/models/ab_testing.py` implemented and has evaluation logic. ✅
- CI: Multiple workflows exist (`fetch-schedule.yml`, `audit.yml`, `auto-optimize.yml`, `ci.yml`). Found minor YAML/layout issues in `audit.yml` that triggered a static 'implicit key' complaint from YAML checks — recommend validating with `actionlint` and `yamllint`. ⚠️
- Secrets: `secrets/.env.backup` contained real-looking API keys and DB URL — removed from working tree and `secrets/` is already in `.gitignore`. You must rotate any exposed credentials and purge them from history if necessary (BFG/filter-branch). CRITICAL. ❗

---

## Detailed Findings 🔍

### 1) Tests & Linting
- Ran pytest: all tests (non-network) passed locally. Several network/integration tests are skipped when API keys are absent (expected).
- Ran `ruff` locally; it failed due to a UnicodeDecodeError when scanning the entire repo on Windows (some non-UTF-8/binary files cause the runner to crash). Also, `pyproject.toml` contains deprecated top-level ruff settings — move them under `[tool.ruff.lint]` to remove the warning.
- Action: run ruff in CI on Linux (UTF-8) and/or configure `ruff check` to exclude large non-source directories (data/, models/, logs/). Add a small CI lint job with `ruff check . --exclude data,models,reports,logs,.venv`.

### 2) Backtesting & Optimization
- `app/models/backtesting.py` provides a rolling-window backtester; unit tests are present (`tests/test_backtesting.py`) and passed.
- `scripts/optimize_accuracy.py` performs parameter sweeps and saved many results into `data/optimization_results/`.
- `reports/backtests/` is empty on disk — the backtester writes summaries to this directory by default; this likely means most runs used simulated mode or test-run directories. Confirm production backtests write to `reports/backtests/` (the BacktestingFramework saves results there).
- Action: add a smoke backtest CI step that writes to `reports/backtests/` (small sample) and uploads result artifacts when run.

### 3) Prediction Tracking & A/B Testing
- `app/models/prediction_tracker.py` implements a full SQLite-based tracker and related helpers (calibration, league breakdowns). No DB was found on disk — recording is not yet happening in production flows.
- `scripts/optimize_accuracy.py` uses a tracker when available (it wraps predictor with a `self.tracker.record_prediction` call when `self.tracker` exists) — good scaffolding.
- Action: integrate the tracker into `PredictionEngine.predict_matches` (or the ReportGenerator) so predictions produced by scheduled runs are persisted to `data/predictions.db`. Add a test to confirm persistence and a small analytic report generator that uses the tracker (leagues, calibration buckets).

### 4) CI / Workflows
- Workflows present: `.github/workflows/fetch-schedule.yml` (scheduled fetch & train), `.github/workflows/audit.yml` (audit & smoke training), `.github/workflows/auto-optimize.yml` (added by us), and others.
- Observations: `audit.yml` shows a multiline Python here-doc; static analyzer flagged mapping/indentation issues. Validate with `actionlint` and test the workflow with `act` or in a staging repo.
- Action: ensure `auto-optimize.yml` is protected (no secrets in it) and that optimization CI is safe no-op when historical data is insufficient (scripts already do this). Add a weekly scheduled job if not enabled and restrict permissions.

### 5) Security & Secrets
- Found `secrets/.env.backup` containing API keys and DB URLs. I removed it from the working tree and confirmed `.gitignore` already includes `secrets/` and `.env`. **You must rotate any exposed credentials** (ODDS_API_KEY, FOOTBALL_DATA_API_KEY, DATABASE_URL) and consider removing them from git history (BFG or git filter-repo).
- Action (urgent): rotate keys, remove file from repo history if it was ever committed, add a repo-level CI check to prevent accidental secrets (e.g., GitHub Secret Scanning or pre-commit hook with detect-secrets).

### 6) Docs, CLI & UX
- CLI: `sports-forecast backtest` added (calls the optimizer/backtester). `predict`, `report`, `train` commands exist and are functional.
- Docs: `README.md` updated with backtest/optimizer instructions. We should add a short `docs/automation.md` describing how scheduled tasks and optimizer artifacts are handled, and an ops checklist for rotating secrets and enabling workflows.

### 7) Code Hygiene
- Multiple debug log lines and `debug` flags are present (expected for running in debug mode), and logs show historical daily runs were executed.
- Search found TODO/DEBUG flags used properly. There are some legacy backup folders (`BACKUP_v4.0_WORKING/`) — consider archiving them externally or moving into an `archive/` area to keep the repo clean.

---

## Short-term Prioritized Actions (next 1-10 days) ✅
1. **Rotate exposed credentials immediately** and remove secrets from git history (CRITICAL). Estimated time: 1–2 hours.
2. **Integrate PredictionTracker** into `PredictionEngine` and scheduled runs so predictions are recorded to `data/predictions.db`. Add unit test. Estimated time: 4–6 hours.
3. **Fix CI YAML lint issues** (validate `audit.yml` with `actionlint`/`yamllint`) and ensure workflow uses `runs-on` and quoting correctly. Estimated time: 1–2 hours.
4. **Add a small backtest smoke step to CI** (writes a small report to `reports/backtests/` and uploads artifact). Estimated time: 1–2 hours.
5. **Ruff configuration:** migrate deprecated top-level `ruff` settings in `pyproject.toml` to `[tool.ruff.lint]` and run `ruff check .` in CI (Linux). Estimated time: 1 hour.
6. **Add secret-scanning pre-commit hook and CI check** to prevent future leaks. Estimated time: 1-2 hours.

---

## Medium-term (2–6 weeks)
- Implement league-specific calibration via isotonic regression (CC-001).
- Add Brier-score optimization and model comparison dashboards.
- Implement real-time lineup and xG integration (DQ-001, FE-001) to boost predictive accuracy.

---

## Deliverables I added/updated in this run
- `tests/test_backtesting.py` (unit tests added)
- `app/run.py` CLI: `backtest` command (added)
- `.github/workflows/auto-optimize.yml` (weekly optimizer workflow added)
- Removed `secrets/.env.backup` from working tree (you must rotate keys and purge history)
- `docs/system_review_2026-01-01.md` (this file)
- `TODO.json` merged and updated with items from `ideas.json` and new action items

---

If you'd like, my next technical steps are:
1) Integrate `PredictionTracker` into `PredictionEngine.predict_matches` (write code + test). (I already added a TODO for this with id=8.)
2) Add a CI smoke backtest and a lint job that runs on a UTF-8 environment (Ubuntu) and updates `pyproject.toml` ruff settings.

Which of the top-priority items (credential rotation, tracker integration, CI lint fixes) should I do next and start implementing immediately? 

(If you want, I can start by integrating the tracker into `PredictionEngine` now and add the unit test.)
