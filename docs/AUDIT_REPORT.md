# Audit Report — Visual & Data Integrity (2025-12-22)

## Scope

A repo-wide audit focusing on the report generation pipeline, image rendering reliability, and prediction metadata consistency.

## Summary of Findings

- Fixed a duplicate rendering call in `generate_fast_reports.py` that caused confidence percentage overlap on prediction cards.
- No other duplicate `ax.text` coordinates found in project files (excluded virtualenv and vendor code).
- All `prediction.json` files examined (3) contained required fields and sensible ranges.
- All `prediction_card.png` images inspected (3) passed non-blankness and content heuristics.

## Actions Taken

- Implemented fix in `generate_fast_reports.py` and canonicalized confidence source to `report_accuracy_probability`.
- Added regression tests to catch duplicate draws and to assert JSON ↔ summary consistency.
- Added audit scripts and a GitHub Actions workflow (`.github/workflows/audit.yml`) to run audits and tests on PRs and nightly.
- Regenerated Premier League reports and re-ran audits to confirm correctness.

## Outstanding Recommendations

- Add threshold-based optimization triggers (only run full optimization when >50 completed matches).
- Add test fixtures to simulate finished matches for the optimizer to validate on CI.
- Add a scheduled job to fetch finished match results daily (requires API keys) and a protected branch policy to ensure audits pass before merges.

## Updates (2026-03-23)

- Completed Sprint S3 hardening cycle: calibration, staleness detection, data-gap degradation, ensemble disagreement, synthetic-data rate monitor, secret scanning, and E2E smoke test pipeline.
- Added publish-ready security controls:
  - `detect-secrets` pre-commit hook + `.secrets.baseline`
  - GitHub workflow `.github/workflows/secret-scan.yml` for PR and push checks
  - CI key usage via GitHub secrets (`FOOTBALL_DATA_API_KEY`, `API_FOOTBALL_KEY`, `SMTP_*` in `fetch-results.yml`)
- Added data integrity controls:
  - `SyntheticRateMonitor` verifies synthetic/real ratio with real-min threshold before live signals
  - `ModelStalenessDetector` checks model age, accuracy, and drift
  - `DataGapHandler` downgrades confidence when data fields are missing
- Added artifact sanitation:
  - `data/optimization_results/` and `reports/historical/*.json`/`*.md` now gitignored to avoid large commit pollution
- Recorded final MVP test metrics: 366 passed, 13 skipped, 0 failures.

## Next Steps

- Enforce real data ingestion by setting `FOOTBALL_DATA_API_KEY` and running `scripts/fetch_historical_bulk.py`, then re-run audit validations from this report.
- Add unit test coverage for `collect_historical_results.py` API-driven ingest and reconciliation logic.
- Schedule post-deploy drift cancellation report to confirm daily model calibration with new real results.

## Current Status

- MVP functional, with robust test coverage and formal security checks enabled.
- Remaining risk: synthetic-data mode still required to be updated with minimum 150+ live historical matches before “live betting” grade can be claimed. 
- Issue tracker entries: #25 (PredictionTracker feedback), #45 (Historical backfill), #71 (Large file remediation) are addressed in state and/or completion.

