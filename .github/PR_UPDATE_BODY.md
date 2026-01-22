Title: Add InjuriesConnector with FlashScore/Transfermarkt fallbacks + compliance checklist

Summary:

- Adds `app/data/connectors/injuries.py` which consolidates injury data fetching:
  - Primary: API-Football (RapidAPI)
  - Fallbacks: FlashScore page scanning, Transfermarkt parsing
  - Caching to `data/cache/injuries_<team>_<year>.json`
  - Rate-limit handling: persists a disabled flag when 429s occur
- Parsers and fixtures in `tests/data/` + unit tests under `tests/` validate parsing and fallback behavior
- Integration test for `DataQualityEnhancer.get_player_injury_impact`
- Compliance doc: `docs/SCRAPING_COMPLIANCE.md`
- Auxiliary: `scripts/check_robots.py` + tests, Windows CI workflow, PR template

Files of interest:

- `app/data/connectors/injuries.py` (new)

PR Checklist:

- [ ] **Run integration tests** in CI (add label `run-integration` to this PR or trigger "Integration tests (on label)" workflow dispatch). Ensure `API_FOOTBALL_KEY` is set in repository secrets.
- [ ] **Legal signoff**: confirm ToS/robots policy for FlashScore and Transfermarkt per `docs/SCRAPING_COMPLIANCE.md` and `docs/robots_report.md`.
- [ ] **Assign reviewers** from `legal` and `data-fetch` teams (or use CODEOWNERS).
- [ ] **Confirm monitoring** for 429 events and cache persistence in `data/cache/` during first 24h runs.
- [ ] Add release notes entry and merge when all checks pass.

Files of interest:

- `app/data/connectors/injuries.py` (new)
- `data_quality_enhancer.py` (uses connector)
- `tests/test_injuries_*` and `tests/data/*` (new fixtures & tests)
- `docs/SCRAPING_COMPLIANCE.md` (new)
- `.github/workflows/ci-windows.yml` (new)

How to push & open PR (local steps):

1. Add remote if not set: `git remote add origin git@github.com:ORG/REPO.git` (replace with your URL)
2. Push branch: `git push --set-upstream origin feature/injuries-connector`
3. Create a PR (GitHub UI) or `gh` CLI: `gh pr create --title "Add InjuriesConnector..." --body-file .github/PR_DRAFT.md --base main`

Testing:

- `python -m pytest -q` (all tests pass locally; network tests are skipped)
- Run `python scripts/check_robots.py hosts.txt` to validate robots.txt entries for hosts; include hosts in `hosts.txt`.

Compliance & Robots report:

- Summary of findings: Ran `scripts/check_robots.py`; key findings are in `docs/robots_report.md`.
  - FlashScore: Disallow rules include news/fixtures and several endpoints; scraping may be disallowed for some paths.
  - Transfermarkt: No explicit Disallow rules for `User-agent: *` in observed `robots.txt` (still check ToS).
- Action requested from reviewers: Confirm ToS/robots policy for listed hosts and approve/deny scheduled scraping; suggest required crawl delays or rate-limits.

Links:

- Robots report: `docs/robots_report.md`
- Compliance checklist: `docs/SCRAPING_COMPLIANCE.md`

Notes & reviewer checklist:

- Verify ToS / robots.txt for FlashScore and Transfermarkt prior to enabling scheduled scraping.
- Confirm policy for social scraping (Twitter/X) before adding social connectors.
- Review parsing heuristics and suggest any refinements for target pages.

Labels suggested: `legal-review`, `data-fetch` (if you want me to add reviewers, please specify usernames or say "use CODEOWNERS").
