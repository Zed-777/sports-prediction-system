## Summary of changes

- Add `InjuriesConnector` with API-Football primary and FlashScore/Transfermarkt fallbacks
- Parsers for FlashScore and Transfermarkt + fixtures under `tests/data/`
- Unit & integration tests validating parsing, caching, and `DataQualityEnhancer` integration
- `docs/SCRAPING_COMPLIANCE.md` with a short compliance checklist
- Windows CI workflow `ci-windows.yml` and a robots.txt checker `scripts/check_robots.py`

## Testing

- All tests pass locally (`python -m pytest -q`). See `tests/` for new tests.

## Compliance

- Included `docs/SCRAPING_COMPLIANCE.md` with guidance on robots.txt, ToS checks, caching, attribution.
- Please review scraping targets and confirm compliance before enabling automated scheduled scraping in CI.

## Notes for reviewer

- The connector persists `injuries_disabled_until.json` when API rate limits occur.
- The parser heuristics are intentionally conservative; prefer official APIs where available.
