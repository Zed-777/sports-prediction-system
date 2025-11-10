#!/usr/bin/env python3
"""
Demo script showing the clean system without match folders
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from generate_clean_reports import CleanReportGenerator


def demo():
    print("🎯 Clean Report System Demo - Serie A")
    print("=" * 50)

    generator = CleanReportGenerator()

    # Generate a clean Serie A report
    result = generator.generate_match_report("serie_a")

    print("\n✅ Serie A report generated successfully!")
    print("📁 Files saved to organized directories only (no match folders)")

    # Show directory structure
    from pathlib import Path
    reports_dir = Path("reports")

    print("\n📂 Directory structure:")
    for item in sorted(reports_dir.rglob("*")):
        if item.is_file() and item.suffix in ['.json', '.png']:
            relative_path = item.relative_to(reports_dir)
            print(f"   📄 {relative_path}")

if __name__ == "__main__":
    demo()
