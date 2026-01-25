# Changelog

## [Unreleased]

### Added

- `app/data/connectors/injuries.py`: new InjuriesConnector with API-Football primary source and fallbacks to FlashScore/Transfermarkt (caching, 429 handling, heuristic parsing). See PR #1. ✅
- GitHub Actions workflow `.github/workflows/integration-tests-on-label.yml` to run integration tests when a PR is labeled `run-integration` or via manual dispatch (requires `API_FOOTBALL_KEY` secret).
- Automated results fetcher: `scripts/collect_historical_results.py` supports `--fetch`, `--fetch-all`, `--auto-optimize N`, `--notify`, and `--report` flags.
- Canonical team name mapping: `config/team_name_map.yaml` to improve API result matching.
- Summary report generator: creates Markdown reports with accuracy metrics in `reports/historical/`.
- Auto-optimization trigger: run `scripts/optimize_accuracy.py::AccuracyOptimizer.full_optimization` when completed matches threshold reached.
- Unit tests for fetcher, matching, notifications, report generation.

### Fixed

- Robust prediction tracking: `create_prediction_record` supports both positional and keyword-style calls from predictors.
- Improved error handling for API fetch and update flows.
