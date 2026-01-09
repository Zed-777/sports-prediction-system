"""Audit prediction.json files for required fields and sensible values.

Checks performed:
- Required keys exist: 'report_accuracy_probability' or 'confidence', 'data_quality_score', 'home_team', 'away_team', 'date'
- Numeric values are in sensible ranges (0-1 for probabilities, 0-100 for scores)
- Presence of summary.md and prediction_card.png in the match folder

Usage:
  python scripts/audit_prediction_jsons.py
"""

import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
matches = list(root.glob("reports/leagues/*/matches/*/prediction.json"))

print(f"Found {len(matches)} prediction.json files to audit")
issues = []

for p in matches:
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        issues.append((p, "invalid_json", str(e)))
        continue

    # required fields
    missing = []
    if "report_accuracy_probability" not in data and "confidence" not in data:
        missing.append("report_accuracy_probability|confidence")
    if "data_quality_score" not in data:
        missing.append("data_quality_score")
    for key in ("home_team", "away_team", "date"):
        if key not in data:
            missing.append(key)

    if missing:
        issues.append((p, "missing_fields", missing))
        continue

    # type/value checks
    rap = data.get("report_accuracy_probability", None)
    if rap is not None:
        try:
            rapf = float(rap)
            if not (0.0 <= rapf <= 1.0):
                issues.append((p, "report_accuracy_probability_out_of_range", rapf))
        except Exception:
            issues.append((p, "report_accuracy_probability_nonfloat", rap))

    dqs = data.get("data_quality_score", None)
    try:
        dqs_f = float(dqs)
        if not (0.0 <= dqs_f <= 100.0):
            issues.append((p, "data_quality_score_out_of_range", dqs_f))
    except Exception:
        issues.append((p, "data_quality_score_nonfloat", dqs))

    # presence of summary and image
    summary = p.parent / "summary.md"
    img = p.parent / "prediction_card.png"
    if not summary.exists():
        issues.append((p, "missing_summary"))
    if not img.exists():
        issues.append((p, "missing_image"))

if issues:
    print("Issues found:")
    for it in issues:
        print(it)
    raise SystemExit(2)
else:
    print("No issues found")
    raise SystemExit(0)
