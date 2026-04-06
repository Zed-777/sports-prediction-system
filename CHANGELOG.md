# Changelog

## [4.1.0] - 2026-04-06

### Added

- **Automated Learning System**: Full GitHub Actions workflow for continuous ML model improvement
  - Daily learning cycle at 4:00 AM UTC via `.github/workflows/daily-learning.yml`
  - Auto-baseline predictions (1 per league daily) for continuous drift detection
  - Implemented `scripts/generate_baseline_predictions.py` for autonomous learning
  - Prediction result tracking and accuracy feedback loop

- **Enhanced Automation Architecture**:
  - Switched from Windows Task Scheduler to GitHub Actions (cloud-native, zero-setup)
  - All 5-step learning cycle: Collect → Track → Optimize → Baseline → Commit
  - Database-backed learning (`data/predictions.db`) separate from user reports
  - Conflict-free design: auto-generated reports ephemeral, DB immutable

- **Infrastructure & Quality**:
  - Fixed Dockerfile to reference only existing requirements files
  - Cleaned VS Code settings (removed pyrightconfig.json conflicts)
  - Added .yamllint configuration for GitHub Actions schema validation
  - Comprehensive GitHub Actions workflows (16 total: CI, testing, learning, scanning)

- **Documentation**:
  - MPDP.md: Complete automation architecture and learning loop documentation
  - Architecture diagrams updated for automated learning system
  - AGENT_HANDOFF.md: Zero-touch automation setup instructions

### Fixed

- Updated Dockerfile dependencies: removed non-existent requirements_phase2*.txt references
- Fixed GitHub Actions secrets context warnings (valid expressions, false positive linting)
- Python analysis conflicts in VS Code (pyrightconfig.json now authoritative)
- Markdown heading in AGENT_PRACTICE_STANDARDS.md (MD041)

### Changed

- Learning loop now fully autonomous - runs daily without manual intervention
- Default automation: GitHub Actions (primary) over Windows Task Scheduler
- Baseline predictions now integrated into main learning workflow

### Technical Details

- **Version**: 4.1.0 (automated learning system)
- **Python**: 3.11 (GitHub Actions) / 3.14.0 (local development)
- **Status**: Production-ready, continuous learning active
- **Learning Data**: Committed daily to `data/historical/`, tracked in `data/predictions.db`

---

## [Unreleased]

### Under Investigation


