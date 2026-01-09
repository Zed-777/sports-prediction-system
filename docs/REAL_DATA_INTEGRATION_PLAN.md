# Real Data Integration Plan (Injury, Referee, Team News)

This document summarizes the recommended steps to fully enable real-data-driven reporting for injuries, referee statistics, and team news.

## Goals

- Replace any remaining placeholder/synthetic data with real API sources.
- Provide clear provenance and fallback logic when data is missing.
- Keep connectors robust and optional (enabled only when API keys are provided).

## Recommended APIs

1. API-Football (RapidAPI)
   - Pros: well-structured, includes fixtures, squads, and injury endpoints in some plans.
   - Usage: set `API_FOOTBALL_KEY` in `.env` (`X-RapidAPI-Key`). The connector lives in `data_quality_enhancer.py` (`_fetch_injury_data_api_football`).
   - Rate limits: depends on RapidAPI plan.

2. Football-Data.org
   - Pros: already in use for fixtures/squads/standings.
   - Limitations: does not provide injury status or suspensions.
   - Usage: continue as a reliable source for squad lists and match data.

3. NewsAPI (optional)
   - Pros: easy way to capture recent club news and lineup/injury mentions.
   - Usage: set `NEWSAPI_KEY` in `.env`. Implemented in `data_quality_enhancer.py` as `_fetch_team_news_data` (placeholder available).

4. Transfermarkt / PhysioRoom (scrape only)
   - Pros: comprehensive injury lists.
   - Cons: scraping is fragile and may violate site terms; use only if acceptable and add caching.

## Implementation Strategy

- Primary source: API-Football injury endpoints. If key present, call `_fetch_injury_data_api_football(team_id)` and convert results with `_analyze_injury_data`.
- Secondary source: Football-Data.org squad lists for basic availability insights (`_fetch_squad_data` + `_analyze_squad_availability`).
- Team news: use NewsAPI when `NEWSAPI_KEY` is provided; analyze top 5-10 articles for lineup/injury mentions and sentiment.
- Referees: continue to parse referee names from fixtures (Football-Data.org), then attempt historical lookup across competitions to compute bias.

## Provenance & UX

- Every data field should include a `data_source` and `data_quality_score` where applicable.
- When real data is missing, show a clear, actionable warning in reports (e.g., "Add API_FOOTBALL_KEY to .env to enable injury data").
- Avoid synthetic fillers; always prefer honest warnings and deterministic fallbacks.

## Testing

- Add unit tests that mock API responses for:
  - Injury payload (happy path + empty payload)
  - Squad fallback
  - NewsAPI parsing
- Add an integration test that runs `generate_fast_reports.py` with no keys to validate graceful fallbacks and with mocked keys to validate parsing.

## Deployment notes

- Store API keys in environment or secrets manager (do not commit to source control).
- Monitor API usage and add exponential backoff for 429 responses.

## Next steps

- If you want, I can implement the API-Football integration fully, add tests, and help configure a RapidAPI subscription for production use.
# Real Data Integration Plan (Injury, Referee, Team News)

This document summarizes the recommended steps to fully enable real-data-driven reporting for injuries, referee statistics, and team news.

## Goals

- Replace any remaining placeholder/synthetic data with real API sources.
- Provide clear provenance and fallback logic when data is missing.
- Keep connectors robust and optional (enabled only when API keys are provided).

## Recommended APIs

1. API-Football (RapidAPI)
   - Pros: well-structured, includes fixtures, squads, and injury endpoints in some plans.
   - Usage: set `API_FOOTBALL_KEY` in `.env` (`X-RapidAPI-Key`). The connector lives in `data_quality_enhancer.py` (`_fetch_injury_data_api_football`).
   - Rate limits: depends on RapidAPI plan.

2. Football-Data.org
   - Pros: already in use for fixtures/squads/standings.
   - Limitations: does not provide injury status or suspensions.
   - Usage: continue as a reliable source for squad lists and match data.

3. NewsAPI (optional)
   - Pros: easy way to capture recent club news and lineup/injury mentions.
   - Usage: set `NEWSAPI_KEY` in `.env`. Implemented in `data_quality_enhancer.py` as `_fetch_team_news_data` (placeholder available).

4. Transfermarkt / PhysioRoom (scrape only)
   - Pros: comprehensive injury lists.
   - Cons: scraping is fragile and may violate site terms; use only if acceptable and add caching.

## Implementation Strategy

- Primary source: API-Football injury endpoints. If key present, call `_fetch_injury_data_api_football(team_id)` and convert results with `_analyze_injury_data`.
- Secondary source: Football-Data.org squad lists for basic availability insights (`_fetch_squad_data` + `_analyze_squad_availability`).
- Team news: use NewsAPI when `NEWSAPI_KEY` is provided; analyze top 5-10 articles for lineup/injury mentions and sentiment.
- Referees: continue to parse referee names from fixtures (Football-Data.org), then attempt historical lookup across competitions to compute bias.

## Provenance & UX

- Every data field should include a `data_source` and `data_quality_score` where applicable.
- When real data is missing, show a clear, actionable warning in reports (e.g., "Add API_FOOTBALL_KEY to .env to enable injury data").
- Avoid synthetic fillers; always prefer honest warnings and deterministic fallbacks.

## Testing

- Add unit tests that mock API responses for:
  - Injury payload (happy path + empty payload)
  - Squad fallback
  - NewsAPI parsing
- Add an integration test that runs `generate_fast_reports.py` with no keys to validate graceful fallbacks and with mocked keys to validate parsing.

## Deployment notes

- Store API keys in environment or secrets manager (do not commit to source control).
- Monitor API usage and add exponential backoff for 429 responses.

## Next steps

- If you want, I can implement the API-Football integration fully, add tests, and help configure a RapidAPI subscription for production use.
