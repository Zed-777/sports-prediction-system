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

## Next Steps

- Open a PR with these changes, merge after review, and monitor the first nightly run of the new audit workflow.
