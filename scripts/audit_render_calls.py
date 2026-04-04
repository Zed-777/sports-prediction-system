"""Scan Python files for `ax.text` calls and report duplicate coordinate usages

This simple audit helps find places where the same coordinates are used multiple
times (which can cause overlapping text when different values are drawn).

Usage:
  python scripts/audit_render_calls.py
"""

import re
from pathlib import Path

PAT = re.compile(
    r"ax\.text\s*\(\s*([-+]?[0-9]*\.?[0-9]+)\s*,\s*([-+]?[0-9]*\.?[0-9]+)\s*,",
)

root = Path(__file__).resolve().parents[1]
# Limit to project files only (exclude virtualenvs and external packages)
pyfiles = [
    p
    for p in root.rglob("*.py")
    if ".venv" not in str(p)
    and "site-packages" not in str(p)
    and ".git" not in str(p)
    and "BACKUP_v4.0_WORKING" not in str(p)
]

duplicates = {}
occurrences = []

for p in pyfiles:
    try:
        text = p.read_text(encoding="utf-8")
    except Exception as e:
        # Skip files that cannot be decoded (binary, vendor files, etc.)
        print(f"[WARN] Skipping {p} due to read error: {e}")
        continue

    for m in PAT.finditer(text):
        try:
            x = float(m.group(1))
            y = float(m.group(2))
        except Exception:
            continue
        line_no = text[: m.start()].count("\n") + 1
        # Protect against malformed files with fewer lines than expected
        lines = text.splitlines()
        snippet = lines[line_no - 1].strip() if line_no - 1 < len(lines) else ""
        key = (x, y)
        occurrences.append((p, line_no, x, y, snippet))
        duplicates.setdefault(key, []).append((p, line_no, snippet))

# Report duplicates (coords used more than once in the repo)
print("Render coordinates occurrences: total=", len(occurrences))
print()
issue_found = False
for coords, occ in sorted(duplicates.items(), key=lambda t: -len(t[1])):
    if len(occ) > 1:
        issue_found = True
        print(f"Coordinates {coords} used {len(occ)} times:")
        for p, ln, snippet in occ:
            print(f"  - {p}:{ln}: {snippet}")
        print()

if not issue_found:
    print("No duplicated ax.text coordinates found.")
else:
    print("Potential overlapping text issues found at the coordinates above.")

# Exit with non-zero code if issues found (for CI integration)
import sys

if issue_found:
    sys.exit(2)
else:
    sys.exit(0)
