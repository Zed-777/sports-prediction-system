#!/usr/bin/env python3
"""Check environment helper for SportsPredictionSystem
Prints python info, whether venv is active, installed key packages, .env keys found (not values).
"""

import importlib.util
import sys
from pathlib import Path

print("python_executable:", sys.executable)
print("python_version:", sys.version.split()[0])
print("is_venv:", sys.prefix != getattr(sys, "base_prefix", sys.prefix))

pkgs = ["requests", "dotenv", "pytest", "yaml", "pandas"]
for p in pkgs:
    spec = importlib.util.find_spec(p)
    print(f"{p}:", "INSTALLED" if spec else "MISSING")

# .env keys
proj = Path(__file__).parent.parent
envp = proj / ".env"
if envp.exists():
    keys = []
    for line in envp.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k = line.split("=", 1)[0].strip()
            keys.append(k)
    print(".env keys:", ", ".join(keys) if keys else "(none)")
else:
    print(".env keys: (file not found)")

# Note: For GitHub token verification and gh auth, we run separate tools
