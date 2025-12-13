"""Validate YAML files that commonly trigger editor Problems.

Checks:
- Parse all files under .github/workflows/*.yml with PyYAML
- Parse docker-compose.yml and report parse errors
- Report presence of TAB characters which many linters disallow

Exit code: 0 if all files parse and have no tabs; 1 otherwise.
"""
import sys
from pathlib import Path

try:
    import yaml
except Exception:  # pragma: no cover - best-effort in local dev
    print("PyYAML not installed. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

root = Path(__file__).resolve().parents[1]
errors = 0

def check_file(p: Path):
    global errors
    text = p.read_text(encoding="utf-8")
    if "\t" in text:
        print(f"TAB_CHAR: {p}")
        errors += 1
    try:
        yaml.safe_load(text)
    except Exception as e:
        print(f"YAML_ERROR: {p}: {e}")
        errors += 1

wf_dir = root / ".github" / "workflows"
for f in sorted(wf_dir.glob("*.yml")):
    check_file(f)

dc = root / "docker-compose.yml"
if dc.exists():
    check_file(dc)

if errors:
    print(f"Validation finished: {errors} problem(s) found.")
    sys.exit(1)
else:
    print("Validation finished: no YAML problems found.")
    sys.exit(0)
