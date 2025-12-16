# Changelog

## [Unreleased]

### Added
- Automated results fetcher: `scripts/collect_historical_results.py` supports `--fetch`, `--fetch-all`, `--auto-optimize N`, `--notify`, and `--report` flags.
- Canonical team name mapping: `config/team_name_map.yaml` to improve API result matching.
- Summary report generator: creates Markdown reports with accuracy metrics in `reports/historical/`.
- Auto-optimization trigger: run `scripts/optimize_accuracy.py::AccuracyOptimizer.full_optimization` when completed matches threshold reached.
- GitHub Actions workflow `.github/workflows/fetch-results.yml` to run the fetcher daily and commit updated historical files.
- Unit tests for fetcher, matching, notifications, report generation.

### Fixed
- Robust prediction tracking: `create_prediction_record` supports both positional and keyword-style calls from predictors.
- Improved error handling for API fetch and update flows.

