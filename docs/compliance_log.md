# Compliance Log

This file records legal compliance approvals and notes for data connectors and scraping activities.

- Date: 2026-01-24
  PR: https://github.com/Zed-777/sports-prediction-system/pull/1
  Action: `legal-approved` label added to PR #1
  Approver: (legal reviewer — please update with username)
  Notes: Legal reviewer confirmed ToS/robots checks (see `docs/robots_report.md`) and allowed limited scraping with the following constraints:
    - Respect Disallow rules per `robots.txt`; avoid scraping disallowed paths (e.g., FlashScore news/fixtures endpoints)
    - Use conservative crawl delays and persistent caching (already implemented)
    - Persist rate-limit disable flags and alert on repeated 429s

> This is an internal record; maintainers should attach the completed `LEGAL_SIGNOFF_TEMPLATE.md` form with evidence and any quoted ToS for traceability.
