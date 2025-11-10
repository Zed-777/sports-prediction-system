#!/usr/bin/env python3
"""Generate La Liga match quickly"""
from generate_clean_reports import CleanReportGenerator

generator = CleanReportGenerator()
result = generator.generate_match_report("la_liga")
print("✅ La Liga match generated successfully!")
