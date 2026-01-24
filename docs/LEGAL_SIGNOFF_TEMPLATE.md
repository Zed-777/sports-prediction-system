# Legal Signoff Template

Use this checklist when approving scraping/connectors for a PR. Fill the approver name and date and attach any supporting notes or screenshots of terms of service / correspondence.

- PR: [link to PR]
- Approver: @
- Date: YYYY-MM-DD

Checklist:
- [ ] Confirmed that targeted hosts' Terms of Service (ToS) allow automated data collection for the intended use.
- [ ] Confirmed `robots.txt` for each host and recorded Disallow rules (see `docs/robots_report.md`).
- [ ] Confirmed whether crawl delays or rate-limits are required and recorded recommended crawl delay.
- [ ] Confirmed whether attribution/acknowledgement is required by ToS and how it will be applied.
- [ ] Confirmed no personal data or PII is being collected in violation of privacy laws.
- [ ] Confirmed the intended use is permitted under local law and platform policies.
- [ ] Recommended any scope restrictions or mitigations (e.g., limit endpoints, add backoff, require manual approval for schedule).

Notes / evidence:

- Attach links or short quotes from ToS that justify approval.

> **Important:** This template is for recording legal review and guidance; it is not a substitute for formal legal counsel where required.