# USB Transfer Checklist

Simple steps to copy the STATS folder to a USB drive and run it on another Windows machine.

1) Create a transfer ZIP (recommended):

   From the project root in PowerShell:

   .\deploy\prepare_for_transfer.ps1

   This produces a ZIP like: STATS_transfer_20251029_153000.zip

2) Copy the ZIP to your USB drive and plug the USB into the target computer.

3) Extract the ZIP on the target computer to a folder, e.g. C:\STATS

4) On the target computer, open PowerShell in the extracted folder and run:

   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt

5) Run a quick smoke test (offline fixtures are included):

   $env:PYTHONPATH='C:\path\to\STATS'; python -m pytest -p no:pytest_asyncio tests/test_integration_flashscore.py -q
   python generate_fast_reports.py generate 1 matches for la-liga

Notes:

- The prepare script excludes large caches and virtual environments to keep the transfer small.
- Do not copy `.venv` or `models/ml_enhanced` unless you want a large transfer; recreate the venv on the target machine.
- Keep API keys out of the archive. Use `.env.example` and set real secrets on the target machine.
- If you need to move cached models or large artifacts, copy `models/` and `data/snapshots/` separately.
