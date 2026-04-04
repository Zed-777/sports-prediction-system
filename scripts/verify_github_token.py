#!/usr/bin/env python3
"""Verify GitHub Personal Access Token (PAT) is valid by calling the user endpoint.
Usage: python scripts/verify_github_token.py
Reads env var GITHUB_TOKEN or .env file in project root.
"""

import os
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).parent.parent


def read_env_file():
    p = PROJECT_ROOT / ".env"
    if not p.exists():
        return {}
    vals = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip()
    return vals


def get_token():
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    vals = read_env_file()
    return vals.get("GITHUB_TOKEN")


def verify_token(token: str) -> dict:
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    r = requests.get("https://api.github.com/user", headers=headers, timeout=10)
    if r.status_code == 200:
        return r.json()
    r.raise_for_status()


def main():
    t = get_token()
    if not t:
        print(
            "GITHUB_TOKEN not found in environment or .env. Use scripts/setup_github_pat.ps1 to save one.",
        )
        sys.exit(2)
    try:
        info = verify_token(t)
        print(
            f"Token valid. Authenticated as: {info.get('login')} (id={info.get('id')})",
        )
        return 0
    except Exception as e:
        print(f"Token verification failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
