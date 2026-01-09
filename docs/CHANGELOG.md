# Changelog

## [Unreleased]

### Fixed

- Fixed overlapping confidence percentage rendering in `prediction_card.png` by removing duplicate draws and canonicalizing the confidence source to `report_accuracy_probability`. Added regression tests and audit scripts to prevent recurrence. (2025-12-22)

### Added

- Added audit scripts: `scripts/audit_render_calls.py`, `scripts/audit_prediction_jsons.py`, `scripts/audit_images.py` to validate rendered reports and JSONs.
- Added CI workflow `.github/workflows/audit.yml` to run tests and audits on PRs and nightly.
