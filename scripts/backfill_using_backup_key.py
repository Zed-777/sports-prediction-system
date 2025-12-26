#!/usr/bin/env python3
"""
Helper: Run fetch_historical_api.py for specified seasons using FD key loaded from secrets/.env.backup.
Reports which seasons succeed and which fail due to 403 or other errors.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
BACKUP = ROOT / "secrets" / ".env.backup"
SCRIPT = ROOT / "scripts" / "fetch_historical_api.py"
VENV_PY = ROOT / ".venv-Z1.1" / "Scripts" / "python.exe"


def read_fd_key():
    if not BACKUP.exists():
        return None
    text = BACKUP.read_text(encoding="utf-8")
    m = re.search(r"^FOOTBALL_DATA_API_KEY\s*=\s*(.*)$", text, flags=re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def run_for_season(season):
    key = read_fd_key()
    if not key:
        print("No FD key found in secrets/.env.backup")
        return False, "no-key"
    env = {"FOOTBALL_DATA_API_KEY": key}
    cmd = f'"{VENV_PY}" "{SCRIPT}" --fd --competition PD --seasons {season} --outfile fd_pd_{season}.csv'
    print(f"Running: {cmd}")
    try:
        subprocess.run(cmd, shell=True, check=True, env=env)
        return True, "saved"
    except subprocess.CalledProcessError as e:
        return False, str(e)


def main():
    seasons = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
    results = {}
    for s in seasons:
        ok, status = run_for_season(s)
        results[s] = (ok, status)
    print("\nSummary:")
    for s, r in results.items():
        print(f"{s}: {'OK' if r[0] else 'FAILED'} -> {r[1][:120]}")


if __name__ == "__main__":
    main()
