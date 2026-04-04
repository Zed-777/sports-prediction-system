"""Validate YAML files that commonly trigger editor Problems.

Checks:
- Parse all files under .github/workflows/*.yml with PyYAML
- Parse docker-compose.yml and report parse errors
- Report presence of TAB characters which many linters disallow

Exit code: 0 if all files parse and have no tabs; 1 otherwise.
"""

import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("validate_yaml")

try:
    import yaml
except ImportError:  # pragma: no cover - best-effort in local dev
    logger.error("PyYAML not installed. Install with: pip install pyyaml")
    sys.exit(2)

root = Path(__file__).resolve().parents[1]


def check_file(p: Path) -> int:
    """Check a YAML file for whitespace and parse issues, returning count of problems."""
    issues = 0
    text = p.read_text(encoding="utf-8")
    if "\t" in text:
        logger.error("TAB_CHAR: %s", p)
        issues += 1
    try:
        yaml.safe_load(text)
    except yaml.YAMLError as e:
        logger.error("YAML_ERROR: %s: %s", p, e)
        issues += 1
    return issues


wf_dir = root / ".github" / "workflows"
errors = 0
for f in sorted(wf_dir.glob("*.yml")):
    errors += check_file(f)

dc = root / "docker-compose.yml"
if dc.exists():
    errors += check_file(dc)

if errors:
    print(f"Validation finished: {errors} problem(s) found.")
    sys.exit(1)
else:
    print("Validation finished: no YAML problems found.")
    sys.exit(0)
