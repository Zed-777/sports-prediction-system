Developer setup for STATS (quick)

Purpose

This file lists the concrete tools, versions and steps a new developer or agent will need to run and maintain the project locally on Windows. It is intentionally short and copy-paste friendly.

Minimum platform

- Windows 10/11 or Linux/macOS (instructions below assume Windows PowerShell)
- Python 3.9+ (3.10 or 3.11 recommended)

Quick steps (Windows PowerShell)

1) Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Install runtime requirements

```powershell
pip install -r requirements.txt
```

3) Install developer tools (optional but recommended)

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

- Run a smoke generator using fixtures:

```powershell
python generate_fast_reports.py generate 1 matches for la-liga
```

Troubleshooting

- If `ruff` or other dev packages are missing, install via `pip install -r requirements-dev.txt`.
- If tests fail due to missing optional plugins (like `pytest_asyncio`), rerun pytest disabling the plugin: `-p no:pytest_asyncio` is used above as a safe fallback.

Next steps you can perform (optional)

- Add `requirements-dev.txt` to CI so dev tools run in pipeline.
- Pin package versions in `pyproject.toml` or add a lockfile for reproducibility.

Contact / Notes

- Keep secrets out of transfers: use `.env.example` and set real API keys on the target machine.
- The `deploy/prepare_for_transfer.ps1` script will create a ZIP suitable for USB transfer and excludes `.venv`, large caches, and logs by default.
