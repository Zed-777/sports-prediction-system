# Copilot Instructions for SportsPredictionSystem (Phase 2 Lite)

Compact reference for AI coding agents working in this repo. Keep edits small, add focused tests, and prefer importing functions from `app/` modules instead of running scripts in tests.

Core entrypoints (quick checks)
- `python phase2_lite.py` — Phase 2 Lite harness (smoke)
- `python generate_fast_reports.py` — create report outputs
- `app/cli.py` / `app/run.py` — integrated CLI flows (preferred for full pipelines)

Quick setup (Windows PowerShell)
```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
```
Use `.env.example` → `.env` for local API keys (never commit secrets).

Project conventions and patterns to follow
- Data lives under `data/` with subfolders: `raw/`, `processed/`, `cache/`, `snapshots/`. Scripts expect these layouts.
- Models/artifacts are stored in `models/`. Keep deterministic filenames for reproducibility.
- Tests live at repo root and `tests/`. Example unit test: `test_enhanced_ingestion.py`.
- Small scripts (one-off runners) use the pattern `if __name__ == '__main__':` — prefer calling exposed functions from `app/` modules in tests instead of executing scripts directly when possible.

Integration points & external services
- External APIs referenced in docs and code: Football-Data.org, API-Football, Ball Don't Lie, Open-Meteo, The Odds API. Look for connectors in `app/data/` and `legacy_files/`.
- Caching: many ingestion scripts write to `data/cache/` and `data/expanded_cache/`. Reuse caching utilities in `app/utils/` when available.

Project conventions (concrete, actionable)
- New ingestion connector: implement in `enhanced_data_ingestion.py`, write outputs to `data/raw/`, add validation in `data_quality_enhancer.py`, and include a compact test fixture in `tests/data/`.
- Add models under `app/models/`, add a CLI flag in `app/cli.py`, and include a deterministic smoke test in `tests/`.

Testing & CI notes
- Run tests locally: `python -m pytest -q` — prefer small fixtures to keep CI fast.
- Smoke checks after edits: `python phase2_lite.py` and `python generate_fast_reports.py generate 1 matches for la-liga`.
- When adding CI: include a Windows runner for platform-specific checks and a synthetic-detection job (details in MPDP.md backlog).

If you want this expanded (onboarding checklist, GitHub Actions snippets, sample fixtures), say which area to expand and I will iterate.

**Compliance & scraping**: See `docs/SCRAPING_COMPLIANCE.md` for a short legal checklist, robots.txt guidance, and caching/attribution best-practices when adding scrapers.
Appendix & references

- For implementation details and deep dives, see `docs/` (e.g., `docs/ML_ADVANCED_MODEL_PLAN.md`, `docs/flashscore_debug.md`) and `README.md`.
- If you'd like, I can add a one-page onboarding checklist (Windows scheduled task examples + GitHub Actions snippets with a Windows runner and a synthetic-detection job). Tell me which and I'll add it.

