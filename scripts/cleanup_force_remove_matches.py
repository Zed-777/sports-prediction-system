#!/usr/bin/env python3
"""
Force-remove match directories under reports/leagues/*/matches.

This script is conservative:
- It only removes directories directly under reports/leagues/*/matches
- It skips files named .keep or .gitkeep
- It attempts to fix common Windows permission issues (remove read-only) and retries
- It reports which directories were removed and which failed

Usage:
  python scripts/cleanup_force_remove_matches.py --dry-run  # shows what would be removed
  python scripts/cleanup_force_remove_matches.py           # performs removal

Be careful: this permanently deletes match directories and their files.
"""

from pathlib import Path
import shutil
import os
import stat
import argparse

ROOT = Path(__file__).parent.parent
REPORTS = ROOT / "reports" / "leagues"


def on_rm_error(func, path, exc_info):
    """Error handler for shutil.rmtree: try to change permissions and retry."""
    try:
        os.chmod(path, stat.S_IWRITE)
    except Exception:
        pass
    try:
        func(path)
    except Exception:
        raise


def collect_match_dirs() -> list:
    dirs = []
    if not REPORTS.exists():
        return dirs
    for league_dir in REPORTS.iterdir():
        matches_dir = league_dir / "matches"
        if matches_dir.exists() and matches_dir.is_dir():
            for child in matches_dir.iterdir():
                if child.is_dir() and child.name not in (".keep", ".gitkeep"):
                    dirs.append(child)
    return dirs


def remove_dir(path: Path) -> tuple[bool, str]:
    try:
        shutil.rmtree(path, onerror=on_rm_error)
        return True, ""
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="Force remove report match directories")
    parser.add_argument("--dry-run", action="store_true", help="List directories that would be removed")
    parser.add_argument("--confirm", action="store_true", help="Bypass interactive confirmation")
    args = parser.parse_args()

    match_dirs = collect_match_dirs()
    if not match_dirs:
        print("No match directories found to remove.")
        return

    print(f"Found {len(match_dirs)} match directories under reports/leagues/*/matches")
    for d in match_dirs:
        print(" - ", d)

    if args.dry_run:
        print("Dry run: no directories will be removed.")
        return

    # Require both explicit confirmation and an environment permit to avoid accidental runs
    if not args.confirm or os.getenv("PRUNE_ALLOWED") != "1":
        print("Aborted: destructive operation requires both --confirm and PRUNE_ALLOWED=1 in the environment.")
        return

    removed = []
    failed = []
    for d in match_dirs:
        ok, err = remove_dir(d)
        if ok:
            removed.append(d)
        else:
            failed.append((d, err))

    print(f"Removed: {len(removed)} directories")
    for d in removed:
        print("  • ", d)
    if failed:
        print(f"Failed to remove: {len(failed)} directories")
        for d, e in failed:
            print("  x", d, "->", e)
        print("If failures are due to file locks or permissions, try running this script as Administrator or close any applications (e.g., OneDrive) locking files.")
    else:
        print("All match directories removed successfully.")


if __name__ == '__main__':
    main()
