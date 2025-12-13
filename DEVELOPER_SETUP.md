# Developer setup for STATS (quick)

## Purpose

This file lists the concrete tools, versions and steps a new developer or agent will need to run and maintain the project locally on Windows. It is intentionally short and copy-paste friendly.

Minimum platform

-- Windows 10/11 or Linux/macOS (instructions below assume Windows PowerShell)
-- Python 3.9+ (3.10 or 3.11 recommended). If you plan to install heavy compiled libraries (numpy/pytensor/tensorflow), use Python 3.13 for best binary wheel support on Windows.

Quick steps (Windows PowerShell)

1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

1. Install runtime requirements

```powershell
pip install -r requirements.txt
```

1. Install developer tools (optional but recommended)

```powershell
pip install -r requirements-dev.txt
```

Recommended dev packages (available in `requirements-dev.txt`)

- ruff — fast linter/formatter and auto-fix tool
- pytest — test runner
- pytest-asyncio — plugin for async tests used by some tests (disabled fallback supported)
- mypy — optional static typing checks
- flake8 / black — optional formatting

VS Code recommended extensions

The next agent will find `.vscode/extensions.json` in this repo recommending the following extensions:

- ms-python.python (official Python support and debugging)
- ms-python.vscode-pylance (fast type checking / language server)
- ms-vscode.powershell (PowerShell language support and script debugging)
- njpwerner.autodocstring (docstring helpers)
- eamodio.gitlens (git lens for history and blame)

Optional external tools and notes

- Playwright or Playwright CLI — only required if you want browser-based scraping fallbacks. Playwright is optional here; scraping uses static HTML fixtures by default. If you plan to enable Playwright, install it separately and follow Playwright docs.

- Node.js / npm — only if you plan to run frontend/dashboard builds or Playwright Node harnesses.

PowerShell notes

- Use the PowerShell commands in the README and `deploy/prepare_for_transfer.ps1` for packaging.
- This repository includes Windows-oriented scripts; if you prefer Linux/macOS, adapt commands (activate venv using `source .venv/bin/activate`).

Testing and verification

- Run unit and integration tests (offline fixtures are used so live API keys are not required for the baseline tests):

```powershell
$env:PYTHONPATH='C:\path\to\STATS'; python -m pytest -p no:pytest_asyncio -q
```

If you prefer a one-line helper that installs dev dependencies and sets up the package for development (editable install), use `scripts/dev_setup.ps1`.
This script is idempotent and will skip repeated installs once the `.venv/.dev_installed` marker exists unless you pass `-Force`.

PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev_setup.ps1
```

If you want to also install optional Phase2 heavy dependencies (may require long build time or additional build tools), add `-InstallPhase2`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev_setup.ps1 -InstallPhase2
```

After the setup, use the `scripts/run_tests.ps1` helper to consistently run tests in the same venv (avoids repeated reinstalls and Python mismatch):

```powershell
.\scripts\run_tests.ps1  # runs all tests
.\scripts\run_tests.ps1 -Subset "tests/test_state_sync_file.py,tests/test_reset_status_scripts.py"
```

```powershell
```

If you prefer an interactive helper for common dev tasks, use `scripts/dev_tools.ps1` which will auto-activate the `.venv` before running commands.

This script will install the package in editable mode using `pip install -e .` so that `import app.xxx` works in tests and interactive runs.

- Run a smoke generator using fixtures:

```powershell
python generate_fast_reports.py generate 1 matches for la-liga
```

Troubleshooting

- If `ruff` or other dev packages are missing, install via `pip install -r requirements-dev.txt`.
  - If you want to run Redis-backed tests locally, `fakeredis` is included in `requirements-dev.txt`.
    Install the dev requirements: `pip install -r requirements-dev.txt`.
- If tests fail due to missing optional plugins (like `pytest_asyncio`), rerun pytest disabling the plugin: `-p no:pytest_asyncio` is used above as a safe fallback.

Next steps you can perform (optional)

- Add `requirements-dev.txt` to CI so dev tools run in pipeline.
- Pin package versions in `pyproject.toml` or add a lockfile for reproducibility.

Contact / Notes

- Keep secrets out of transfers: use `.env.example` and set real API keys on the target machine.
- The `deploy/prepare_for_transfer.ps1` script will create a ZIP suitable for USB transfer and excludes `.venv`, large caches, and logs by default.

## Endpoint disable management — `state_sync` (file/Redis)

The project uses `app/utils/state_sync.py` to coordinate a runtime-safe "disabled" state for endpoints when providers return rate-limits (HTTP 429). This is used to avoid repeated failing calls across runs and processes.

Key points:

- Primary store: a JSON file in `data/cache/disabled_flags.json` in a nested host->path structure.
- Optional Redis HSET fallback: if the environment variable `REDIS_URL` is set and `redis` is installed the code uses Redis hashes for per-host keys and path entries.
- Structure: host -> path -> {"disabled_until": `<epoch>`, "reason": "429|backoff|manual", "by": "process-id"}

How to inspect the flags:

- File-based: open `data/cache/disabled_flags.json` or use `python -c "import json; print(json.load(open('data/cache/disabled_flags.json')) )"` to print.
- Redis-based: use `redis-cli HGETALL state_sync:<host>` or a small Python snippet.

How to reset flags:

- File-based: delete or edit `data/cache/disabled_flags.json` manually.
- Redis-based: `redis-cli DEL state_sync:<host>` will remove entries for the host.

How to enable/disable Redis in local test/dev:

- Set the environment variable `REDIS_URL` (e.g., `redis://localhost:6379`) and install `redis` Python package; `app/utils/state_sync.py` will automatically prefer Redis HSET when `REDIS_URL` is present.

## Metrics export to S3 (optional)

- If you'd like to upload metrics to S3, set the environment variable `METRICS_S3_BUCKET` to the bucket name and `METRICS_S3_PREFIX` for the prefix (optional).
- The exporter will attempt to use `boto3` to upload files if `METRICS_S3_BUCKET` is present. This is optional and will not fail the run unless AWS client misconfiguration throws an unhandled exception.

CLI and run-time interactions:

- `generate_fast_reports.py` supports `--no-injuries` to skip optional injuries calls entirely.
- `generate_fast_reports.py` supports `--disable-injuries-ttl <seconds>` to temporarily override the configured disable TTL for injuries endpoints during that run.
- The TTL is configured in `config/settings.yaml` under `data_sources.disable_on_429_seconds` per host and per endpoint path.

Example `config/settings.yaml` fragment:

```yaml
data_sources:
 disable_on_429_seconds:
  rapidapi.com:
   /v3/injuries: 86400  # 24 hours
  api-football.com:
   /v2/players/injuries: 7200  # 2 hours
```

When to use the CLI flags:

- Use `--no-injuries` if you're running quick CI smoke tests or troubleshooting and want to avoid injuries endpoints entirely.
- Use `--disable-injuries-ttl` to override per-host TTLs at run-time when troubleshooting or when provider quotas are known to have reset.

Implementation detail (for developers):

- `app/utils/http.py` calls `state_sync.get_disabled_flag(host, path)` before executing HTTP requests — if a result indicates `disabled_until` is in the future, the call returns a 429-like object immediately.
- On a real HTTP 429 response, `app/utils/http.py` uses `state_sync.set_disabled_flag(host, path, disabled_until)` to persist a TTL according to `config/settings.yaml`.
- `metrics` counters are incremented across the codebase to capture call counts, errors, cache hits, and disabled hits.

This behavior allows both local and multi-process systems to avoid hitting providers when they respond with transient or sustained rate limits.
