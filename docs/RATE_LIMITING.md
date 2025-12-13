# Rate limiting & API failures (best practices)

When using public API providers (Football-Data, API-Football, SportsData), you'll encounter HTTP 429 and sometimes 403/401 responses due to rate limits or permissions. Here are the practical mitigations implemented and recommended:

## Client-side retry with exponential backoff (implemented)

- We added a `safe_request_get` utility in `app/utils/http.py` that does exponential backoff and respects the `Retry-After` header when present.
- Use this helper for high-volume API calls to avoid immediate 429s and to retry transient network issues.

## Rate-limiting and deduping

- Avoid duplicate simultaneous requests for the same resource by adding caching and memoization in your data layer. The code already caches team stats (e.g., `home_away_{team_id}_{league}`) and hits the cache in many cases.
- Add an optional per-provider throttle if your plan limits requests per minute.

## Control concurrency

- If you parallelize HTTP calls (multithreading or multiprocessing), limit the worker pool size to reduce burst traffic.

## Use `Retry-After` header

- The `safe_request_get` implementation handles `Retry-After` by sleeping for the recommended period when provided by the server.
  - Default per-provider `min_interval` is set in `config/settings.yaml` under `data_sources.throttle_by_host`.
  - Current conservative defaults: `api.football-data.org: 1.5s`, `api-football-v1.p.rapidapi.com: 1.2s`, `api.sportsdata.io: 1.0s`, `api.the-odds-api.com: 1.0s`.
  - Adjust these values according to your subscription plan and provider rules.

## Per-endpoint throttling & token buckets (new)

- We now support `data_sources.throttle_by_endpoint` and `data_sources.throttle_bucket_by_endpoint` in `config/settings.yaml`.
- These settings allow you to set `min_interval` or token-bucket parameters for specific path prefixes (e.g., `/v4/competitions`, `/v3/fixtures`).
- Endpoint rules take precedence over host-level rules; matching uses the longest path prefix to pick the specific rule.
- Token buckets allow short bursts (via `capacity`) with a steady refill `rate` (tokens per second). Use them for endpoints that allow occasional bursts but have a steady rate limit.

Example `settings.yaml` snippet:

```yaml
data_sources:
  throttle_by_endpoint:
    api.football-data.org:
      /v4/matches: 1.0
      /v4/competitions: 1.5
    api-football-v1.p.rapidapi.com:
      /v3/fixtures: 1.2

  throttle_bucket_by_endpoint:
    api.football-data.org:
      /v4/matches:
        capacity: 8
        rate: 0.8
```

## How the system applies throttle rules

- On startup, `safe_request_get` will read the `settings.yaml` and register bucket and endpoint settings with the global throttle manager.
- If a token bucket exists for a given endpoint, requests will block until tokens are available; otherwise a `min_interval` delay is applied.
- If neither endpoint nor host-level settings are found, defaults are conservative (`~0.5s`).

## Best practices for tuning per-endpoint settings

- Start conservative: set `min_interval` based on the strictest endpoint you use most often.
- Use token buckets only for endpoints where you occasionally need bursts, e.g., batch endpoint for `/v4/matches`.
- Avoid a token bucket with a very high `rate` in free tiers — it substantially increases your effective request throughput.

## Quick troubleshooting and verification

- Use `scripts/check_throttle_config.py` to print the current throttle mapping the system will apply
- Run a small experiment: set `throttle_by_endpoint` for a host to a large min_interval and confirm that calls observe delays
- Check `reports/` metadata files for per-run metrics of `429/403/401` events to see if the new settings reduce those counts

### Schedule heavy/large fetches for off-peak times

- Bulk historical data pulls should be scheduled as nightly batches with the CLI script (e.g., `collect_historical_data.py`) using a low concurrency and extended backoff.

1. Provide user-friendly fallbacks

- The system already falls back to caching and other data sources (FlashScore) when API calls fail.

1. Monitor & alert

- Instrument and monitor the `api_call_count`, `api_error_count`, and recorded 429/403/401 events. This helps detect whether it’s a plan or quota issue vs. a code issue.

1. Paid tiers & API vendors

- If you frequently exceed rate limits, consider upgrading to a paid plan or request a higher quota from the provider.

1. Respect provider guidelines

- Document per-provider limits and any header requirements. If a provider requires a header-based key (`Ocp-Apim-Subscription-Key`), adapt the connectors accordingly.

If you'd like, I can also:

- Add a per-provider throttle function that keeps requests under X/minute.
- Add a stats summary at the end of `generate_fast_reports.py` showing the combined number of 429/403/401 events and how many retries were executed for each provider.
- Add a minimal test checking `safe_request_get` handles `Retry-After` header correctly.

Suggested per-provider & per-endpoint quota defaults (conservative):

- Football-Data.org (v4):
  - /v4/competitions: 1.5s min_interval (40-ish req/min)
  - /v4/matches: 1.0s min_interval (default endpoint for match lists)
  - /v4/teams: 1.0s min_interval
  - Token bucket (optional): capacity 8, rate 0.8 tokens/sec (~48 tokens/min)

- API-Football (RapidAPI v3):
  - /v3/fixtures: 1.2s min_interval
  - /v3/teams: 1.2s min_interval
  - Token bucket (optional): capacity 6, rate 0.9 tokens/sec (~54 tokens/min)

- Odds & Weather providers (fast-changing data):
  - Odds snapshots (The-Odds-API): TTL 5 minutes, throttle 1.0s
  - Open-Meteo (weather): TTL 30 minutes, throttle 0.5-1.0s depending on usage

Note: These are conservative defaults; actual quotas are dependent on your subscription level. If you provide your subscription tier for each provider (free/paid, plan name), I will adjust the settings accordingly.
