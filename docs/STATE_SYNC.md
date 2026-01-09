# State Sync and endpoint disable TTLs

This document clarifies how `state_sync` coordinates endpoint "disabled" status across processes, how TTLs are configured, and how to use CLI flags and test harnesses.

## Purpose

When HTTP providers respond with 429 (Too Many Requests), we want to avoid repeatedly making calls that fail and potentially trigger longer bans. The `state_sync` module persists a "disabled" flag for an endpoint for a given time (TTL), so that other runs or processes will avoid requesting the endpoint until the TTL expires.

## Stores and fallbacks

- File-based store: `data/cache/disabled_flags.json`
  - This is the default when `REDIS_URL` isn't set.
  - Structure is a nested JSON object structured as: `{ "host": { "/path": {"disabled_until": 169xxx, "reason": "429", "by": "process-id"}}}`

- Redis HSET store (optional): Setting `REDIS_URL` to a proper Redis URL will enable HSET-based storage:
  - Keys follow: `state_sync:<host>`, and values are HSET entries for each `path` with JSON encoded metadata.
  - Ensures multi-process and cluster coordination, suitable for multi-worker production setups.

## Configuration

Add values to `config/settings.yaml` under `data_sources.disable_on_429_seconds` for per-host and per-path TTLs.

Example:

```yaml
data_sources:
  disable_on_429_seconds:
    rapidapi.com:
      /v3/injuries: 86400
    api-football.com:
      /v2/players/injuries: 7200
```

There are three levels of TTL considered (descending priority):

1. Run-time override via `--disable-injuries-ttl` CLI or runtime argument
2. Per-endpoint TTL from `config/settings.yaml`
3. Default fallback (5 mins) configured in code (if no entry found)

## Using CLI flags

- `--no-injuries` completely disables injuries API calls for that run.
- `--disable-injuries-ttl <seconds>` temporarily overrides per-host TTLs for the injuries endpoint for the duration of the run.

Example:

```powershell
python generate_fast_reports.py generate 2 matches for la-liga --no-injuries
python generate_fast_reports.py generate 2 matches for la-liga --disable-injuries-ttl 3600
```

## Developer usage examples

Import `state_sync` and inspect or set values directly in an ad-hoc script:

```python
from app.utils import state_sync

host = 'rapidapi.com'
path = '/v3/injuries'
flag = state_sync.get_disabled_flag(host, path)
print(flag)

# Set the flag manually (e.g., for debugging):
state_sync.set_disabled_flag(host, path, disabled_until=1690000000, reason='manual')

# Remove flag:
state_sync.clear_disabled_flag(host, path)
```

## Inspecting the file-store

- File-based store: open or inspect `data/cache/disabled_flags.json`.
- Redis-based store: use `redis-cli` or a simple Python snippet to HGET keys for `state_sync:<host>`.

## Unit testing

Prefer `fakeredis` for unit tests when validating Redis-backed flows to avoid requiring a real Redis service in CI.

Example in pytest:

```python
import fakeredis
from app.utils import state_sync

  # configure fakeredis-based client and set as redis client inside state_sync for the test
  r = fakeredis.FakeRedis()
  state_sync._set_redis_client_for_tests(r)
Note: The module now includes convenience test helpers: `_set_redis_client_for_tests(client)` and `_clear_redis_client_for_tests()` which can be used to inject a fake redis client for unit tests.

# run tests that call state_sync.set_disabled_flag and assert HSET behavior
```

## Resetting flags

- Delete the JSON file: `rm data/cache/disabled_flags.json` (or delete via PowerShell `Remove-Item -Path data/cache/disabled_flags.json`)
- Redis: `redis-cli DEL state_sync:<host>`

## Notes

- TTLs cooperate with rate limit backoff logic in `app/utils/http.py`. If `http.py` receives a 429, it will persist the TTL and the calling code will see and honor a 429-like response without making an actual HTTP call until TTL expires.
- Use the `--export-metrics` CLI flag to gather metrics collected during runs to help decide whether to increase or decrease TTL values.

---

If you'd like, I can add a simple script `scripts/reset_disabled_flags.py` to automate resets or add a GitHub Actions CI job that validates TTL propagation with `fakeredis`. Tell me which you'd prefer next.
