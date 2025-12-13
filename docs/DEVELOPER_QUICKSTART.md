# Developer Quickstart: Check system status, reset disabled endpoints, export metrics

Use these commands and scripts to quickly get a view of the runtime state and control the endpoint disabled behavior introduced in `state_sync`.

1. Check disabled flags and metrics (local view)

PowerShell:

```powershell
python scripts/status.py
```

Output: prints `disabled` flags (from file or redis) and in-memory metrics. Great for quick checks after running generator.

1. Reset or clear disabled flags

PowerShell:

```powershell
# List flags
python scripts/reset_disabled_flags.py --list

# Clear one host+path
python scripts/reset_disabled_flags.py --host api-football.com --path /v2/players/injuries --clear

# Clear all
python scripts/reset_disabled_flags.py --clear-all
```

1. Run a generator smoke test (no injuries & export metrics)

PowerShell:

```powershell
python generate_fast_reports.py generate 1 matches for la-liga --no-injuries --export-metrics
```

1. Force a CLI run that re-enables injuries for a short TTL

PowerShell:

```powershell
# Temporarily override the configured disable TTL for the injuries endpoint for this run
python generate_fast_reports.py generate 1 matches for la-liga --disable-injuries-ttl 30
```

1. Run unit tests (dev env must be installed) — the Redis test will be skipped if `fakeredis` isn't installed

PowerShell:

```powershell
python -m pytest tests/test_state_sync_file.py -q
python -m pytest tests/test_state_sync_redis.py -q  # requires fakeredis installed
python -m pytest tests/test_reset_status_scripts.py -q
```

Or launch an interactive PowerShell developer tool that wraps the common tasks:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev_tools.ps1
```

This menu helps you run setup, status, tests, reset, or generator runs without memorizing flags.

1. Developer Notes

- Use `DEVELOPER_SETUP.md` or `docs/STATE_SYNC.md` for deep details on `state_sync` and `REDIS_URL`.
- If you want a simpler runtime (no Redis), don't set `REDIS_URL`. The file-based JSON store in `data/cache/disabled_flags.json` is used instead.
- To enable Redis in CI or locally, set `REDIS_URL` to the Redis instance URI (CI does this for smoke test). Make sure `redis` client package is installed.

If you'd like, I can add an interactive PowerShell wrapper (like `scripts/dev_tools.ps1`) that offers these options as simple commands so you can avoid memorizing flags. Tell me if you want that and whether you'd prefer a PowerShell script or a cross-platform Python wrapper.
