#!/usr/bin/env python3
import os
from pathlib import Path

def _read_env_key(key: str) -> str | None:
    """Read a key from .env file if present"""
    env_file = Path('.env')
    if not env_file.exists():
        return None
    with env_file.open() as f:
        for line in f:
            line = line.strip()
            if line.startswith(f'{key}='):
                value = line.split('=', 1)[1]
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                return value
    return None

api_key_env = os.environ.get('API_FOOTBALL_KEY')
api_key_file = _read_env_key('API_FOOTBALL_KEY')
api_key = api_key_env or api_key_file

print(f"From env: {api_key_env!r}")
print(f"From .env file: {api_key_file!r}")
print(f"Combined: {api_key!r}")
print(f"Starts with YOUR_: {api_key.startswith('YOUR_') if api_key else 'N/A'}")
