#!/usr/bin/env python3
import os
import sys

api_key = os.environ.get("API_FOOTBALL_KEY")
print(f"API_FOOTBALL_KEY from os.environ: {api_key!r}")
print(f"sys.executable: {sys.executable}")

# Check if .env exists and has the key
from pathlib import Path

env_file = Path(".env")
if env_file.exists():
    print(f".env exists, contents (first 10 lines):")
    with open(env_file) as f:
        for i, line in enumerate(f):
            if i >= 10:
                break
            if "API_FOOTBALL" in line:
                print(f"  {line.strip()}")
