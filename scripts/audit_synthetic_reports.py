#!/usr/bin/env python3
"""
Audit synthetic reports under reports/simulated/, produce a JSON summary and optionally fail if too many are present.
"""
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path


def scan_simulated_reports(base: Path) -> dict:
    summary = {"total": 0, "by_league": {}, "samples": []}
    for league_dir in sorted((base or Path("reports") / "simulated").glob("*")):
        if not league_dir.is_dir():
            continue
        files = list(league_dir.rglob("prediction.json"))
        count = len(files)
        summary["by_league"][league_dir.name] = count
        summary["total"] += count
        # sample up to 3 files
        for f in files[:3]:
            summary["samples"].append(str(f))
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=7, help="Report how many synthetic reports older than DAYS exist")
    p.add_argument("--fail-if-more-than", type=int, default=None, help="Exit non-zero if total synthetic reports exceed this value")
    p.add_argument("--fail-if-fraction-more-than", type=float, default=None, help="Exit non-zero if fraction synthetic/total reports exceeds this value (0-1)")
    p.add_argument("--out", type=str, default="reports/metrics/simulated_summary.json", help="Output JSON summary file")
    args = p.parse_args()

    base = Path("reports") / "simulated"
    base.mkdir(parents=True, exist_ok=True)

    summary = scan_simulated_reports(base)

    # find files older than X days
    cutoff = datetime.now() - timedelta(days=args.days)
    old_files = []
    for pth in base.rglob("prediction.json"):
        try:
            mtime = datetime.fromtimestamp(pth.stat().st_mtime)
            if mtime < cutoff:
                old_files.append(str(pth))
        except Exception:
            continue

    summary["older_than_days"] = args.days
    summary["old_count"] = len(old_files)
    summary["old_samples"] = old_files[:10]
    summary["scanned_at"] = datetime.utcnow().isoformat() + "Z"

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))

    # Check fraction threshold: compute public reports total
    total_public = 0
    public_dir = Path('reports') / 'leagues'
    if public_dir.exists():
        for pth in public_dir.rglob('prediction.json'):
            total_public += 1

    summary['public_prediction_count'] = total_public
    summary['synthetic_fraction'] = (summary['total'] / (total_public + summary['total'])) if (total_public + summary['total']) > 0 else 0.0

    if args.fail_if_more_than is not None and summary["total"] > args.fail_if_more_than:
        print(f"Failing due to synthetic report count {summary['total']} > {args.fail_if_more_than}")
        raise SystemExit(2)

    if args.fail_if_fraction_more_than is not None and summary['synthetic_fraction'] > args.fail_if_fraction_more_than:
        print(f"Failing due to synthetic fraction {summary['synthetic_fraction']:.2f} > {args.fail_if_fraction_more_than}")
        raise SystemExit(2)

    # otherwise exit 0


if __name__ == "__main__":
    main()
