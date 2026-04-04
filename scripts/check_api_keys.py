#!/usr/bin/env python3
"""Check API keys presence (env / registry) and test a small SportsData API request if available.
This script prints boolean presence for each key and prints HTTP status for SportsData if checked.
It DOES NOT print key values and it should not be used to pass secrets through logs.

NOTE: Do NOT send API keys to anyone (including this assistant). Use secure local stores such as
PowerShell SecretManagement (SecretStore) or a proper cloud secrets manager. To run a command with
secrets available in your session, use `scripts/run_with_secrets.ps1 -Command "python scripts/check_api_keys.py"`.
"""

import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

# Optional: try reading from user registry on Windows if key not present in the current process env
try:
    import winreg
except Exception:
    winreg = None

KEYS = [
    "API_FOOTBALL_KEY",
    "FOOTBALL_DATA_API_KEY",
    "SPORTSDATA_API_KEY",
    "ODDS_API_KEY",
]

out = {}
for k in KEYS:
    v = os.getenv(k)
    if not v and winreg is not None:
        # try to load from HKCU\Environment
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as reg:
                val, _ = winreg.QueryValueEx(reg, k)
                if val:
                    os.environ[k] = val
                    v = val
        except FileNotFoundError:
            pass
        except Exception:
            pass
    out[k] = bool(v)

print("Keys present:", json.dumps(out))

# Test SportsData if the key exists
sd_key = os.getenv("SPORTSDATA_API_KEY")
if sd_key:
    url = "https://api.sportsdata.io/v3/soccer/scores/json/Competitions"
    params = {"key": sd_key}
    try:
        q = "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url + q, timeout=10) as r:
            print("SportsData HTTP status:", r.getcode())
    except urllib.error.HTTPError as e:
        print("SportsData HTTP error code:", e.code)
    except Exception as e:
        print("SportsData request error:", type(e).__name__, str(e))
else:
    print("No SPORTSDATA_API_KEY found; skipping SportsData check")
    # Try to detect whether SecretManagement has a stored secret for SPORTSDATA_API_KEY
    try:
        # Ask PowerShell non-interactively whether a secret with this name exists
        ps_cmd = "try { Get-Secret -Name 'SPORTSDATA_API_KEY' -ErrorAction Stop > $null; Write-Output 'true' } catch { Write-Output 'false' }"
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
        )
        out_ps = completed.stdout.strip()
        if out_ps == "true":
            print(
                "Detected SPORTSDATA_API_KEY in PowerShell SecretManagement. Use `scripts/run_with_secrets.ps1` to run commands with secrets loaded. Example:",
            )
            print(
                "    .\\scripts\\run_with_secrets.ps1 -Command 'python scripts/check_api_keys.py'",
            )
    except Exception:
        # If powershell or SecretManagement not available, ignore silently
        pass

sys.exit(0)
