# SECURITY.md

**Last Updated:** 2026-04-03  
**Status:** Active – Public Release Ready (Pending VULNERABILITY_ASSESSMENT.md Approval)  

---

## 🔐 Vulnerability Reporting

### Report Contact
**Email:** [maintainer@sports-prediction-system.local]  
**Response Time:** Critical (CVSS ≥7.0): within 24 hours  
**Expected Time to Patch:** 1–7 days depending on severity  

**Process:**
1. Send detailed report (steps to reproduce, impact, proof-of-concept) to the contact above
2. Do **not** file public GitHub issues for security-critical findings
3. You will receive acknowledgment within 24 hours
4. Patched version will be released as soon as possible; you'll be credited unless you prefer anonymity

### History
- **2026-03-15:** Dependency security scan (Bandit) completed; no critical findings
- **2026-03-20:** Rate-limiting audit for external APIs; all mitigations in place
- **2026-04-03:** Comprehensive VULNERABILITY_ASSESSMENT.md completed (see that file for full details)

---

## 📦 Dependency Management & Automated Scanning

### Policy
- **Frequency:** Dependencies scanned weekly via GitHub Actions (`.github/workflows/dependency-check.yml`)
- **Automated Updates:** Dependabot enabled; proposes pull requests for security patches automatically
- **Manual Review:** High-impact or breaking changes reviewed by maintainer before merge
- **Pinning Strategy:** All dependencies pinned in [requirements.txt](requirements.txt); lock file in lock/ directory for reproducibility

### Scanning Tools
- **Bandit** (code security): Weekly scans for hardcoded secrets, unsafe functions, injection vulnerabilities
- **Safety / Pip-audit** (dependency CVEs): Weekly checks against known CVE databases
- **Custom scripts** (API key leaks): Pre-commit hook scans for patterns (AWS keys, API tokens, etc.)
- **GitHub Secret Scanning:** Repository-level secret detection enabled

### Critical Dependencies & Security Considerations

| Package | Version | Notes | Risk |
| --- | --- | --- | --- |
| scipy / numpy | ≥1.24.0, 1.10.0 | NumPy <1.24 has known buffer overflow; pinned to safe versions | Low |
| scikit-learn | ≥1.3.0 | Keep up-to-date; CVEs exist in <1.0.10 and <1.2.2 | Low |
| requests | ≥2.31.0 | HTTP library; update frequently for SSL/TLS fixes | Low |
| fastapi / uvicorn | ≥0.104.0 / 0.24.0 | Web framework; security patches released regularly | Low |
| PyYAML | ≥6.0 | Used for config parsing; <6.0 vulnerable to arbitrary code execution | **Medium** |
| SQLAlchemy | ≥2.0.0 | Database ORM; SQL injection protections built-in when using parameterized queries | Low |

See [VULNERABILITY_ASSESSMENT.md](VULNERABILITY_ASSESSMENT.md) for detailed CVE and risk assessment.

---

## 🎯 Threat Model

This system ingests, processes, and reports on historical sports data from public/paid APIs. Key threat vectors:

### 1. **External API Abuse & Rate-Limiting**
**Threat:** Attacker sends massive request volumes to overload external APIs (Football-Data.org, API-Football, Ball Don't Lie, etc.), causing:
- Account suspension or IP ban
- Degraded data quality
- Service outage

**Mitigations:**
- ✅ **Per-host rate limiting** configured in [config/settings.yaml](config/settings.yaml)
- ✅ **Exponential backoff** with 429 (Too Many Requests) responses in `app/utils/http.py`
- ✅ **Caching layer** (`data/cache/`, `data/expanded_cache/`) reduces repeated requests
- ✅ **Graceful fallbacks** when APIs unavailable (use cached/historical data)
- ✅ **Request throttling** in scheduled tasks (weekly/daily, not continuous)

### 2. **Data Injection & Malformed API Responses**
**Threat:** Compromised or malicious API returns crafted payloads that cause:
- Data corruption in predictions
- Pickle deserialization attacks (if used)
- Injection into SQL queries

**Mitigations:**
- ✅ **Input validation** via Pydantic models in [app/types.py](app/types.py) (strict type checking, field validators)
- ✅ **Data quality checks** in [data_quality_enhancer.py](data_quality_enhancer.py) (range checks, consistency validation)
- ✅ **SQL parameterization** via SQLAlchemy ORM (no string concatenation)
- ✅ **No pickle deserialization** in data pipelines (JSON-based or Parquet only)

### 3. **Credential Theft & API Key Exposure**
**Threat:** API keys (API-Football, Football-Data.org, The Odds API, OpenMeteo) leaked in:
- Source code or git history
- Logs or error messages
- Environment variable exposure in CI/CD

**Mitigations:**
- ✅ **Environment variables** for all secrets (loaded from .env, GitHub Secrets in workflows)
- ✅ **.env.example** provided as template; actual .env never committed (in .gitignore)
- ✅ **Pre-commit hook** scans for common secret patterns (see `.github/workflows/secret-scan.yml`)
- ✅ **GitHub Secret Scanning** enabled; alerts on pushes containing known secret formats
- ✅ **Logging:** Secrets are redacted from logs (use custom logger in `app/utils/logging.py` to filter sensitive fields)
- ✅ **CI/CD:** Secrets passed as GitHub Secrets; not echoed in logs or artifacts

**If a secret is exposed:**
1. Immediately rotate the key in your API provider's dashboard
2. Force-push a fix (see [docs/ROTATE_KEYS_AND_SCRUB.md](docs/ROTATE_KEYS_AND_SCRUB.md))
3. Report the incident to affected API providers

### 4. **Scraping & Terms of Service Violations**
**Threat:** Unauthorized or overly aggressive scraping causes:
- IP ban or legal action
- Degraded data quality from fallbacks
- Reputational damage

**Mitigations:**
- ✅ **robots.txt compliance:** Fetched and respected for each domain (see [docs/robots_report.md](docs/robots_report.md))
- ✅ **Terms of Service review:** Each data source reviewed before integration (see [docs/SCRAPING_COMPLIANCE.md](docs/SCRAPING_COMPLIANCE.md))
- ✅ **Preference for APIs:** Official APIs used when available (API-Football, Football-Data.org, Open-Meteo, Ball Don't Lie)
- ✅ **Polite scraping:** Respectful rate limits, User-Agent headers, cache-first approach
- ✅ **Attribution:** Source, URL, timestamp recorded in all data with `provenance` field

### 5. **Data Privacy & Personal Data Leakage**
**Threat:** Personal data (player names, images, social posts) collected/stored in violation of privacy laws (GDPR, CCPA, etc.)

**Mitigations:**
- ✅ **Minimal PII collection:** Only public player/team names, stats, and match results (no email, phone, ID numbers)
- ✅ **No user account data:** System doesn't store user predictions or betting history
- ✅ **Public data only:** Uses only publicly available stats, match results, and official APIs
- ✅ **Data retention:** Historical data retained in `data/historical/` for 3+ years; purge schedule TBD
- ✅ **Data processing transparency:** All data sources and transformations documented in `docs/data-sources.md` and provenance metadata

### 6. **Model Poisoning & Adversarial Attacks**
**Threat:** Attacker feeds bad/biased data to training dataset, causing:
- Model degradation or bias in predictions
- Skewed decision-making for downstream systems

**Mitigations:**
- ✅ **Data validation pipeline:** Multi-layer checks in [data_quality_enhancer.py](data_quality_enhancer.py)
- ✅ **Outlier detection:** Z-score, IQR-based flagging for anomalous match data
- ✅ **Cross-source validation:** Results from multiple APIs compared; discrepancies flagged
- ✅ **Backtesting & holdout tests:** Models evaluated on holdout data; systematic drift detected
- ✅ **Version control:** Models and datasets tracked in git; reproducibility ensured

### 7. **Denial of Service (DoS) on Local System**
**Threat:** Attacker or runaway code exhausts system resources:
- Infinite loops in prediction engine
- Memory exhaustion from large datasets
- Disk exhaustion from unbounded logging

**Mitigations:**
- ✅ **Resource limits:** Prediction timeout (3–4 sec per match); enforced in orchestration layer
- ✅ **Memory limits:** Batch processing with pagination; large datasets processed in chunks
- ✅ **Log rotation:** Logs in `data/logs/` use time/size-based rotation (see logrotate config)
- ✅ **Disk space monitoring:** Data cleanup scripts in `scripts/` (e.g., cache expiry, old artifact deletion)

---

## 🔐 Secret Handling & Key Management

### Environment Variables (Recommended)

```bash
# API Keys
API_FOOTBALL_KEY=your_api_football_key
ODDS_API_KEY=your_odds_api_key
OPEN_METEO_KEY=optional_key

# Database
DATABASE_URL=sqlite:///./data/cache/predictions.db

# System
DEBUG=false
LOG_LEVEL=INFO
```

### Safe Management Practices
1. **Local Development:** Copy `.env.example` → `.env` (never commit `.env`)
2. **GitHub Actions:** Store secrets in repository Settings → Secrets and variables → Actions
3. **Scheduled Tasks (Windows):** Embed secrets in Task Scheduler task definition; encrypt via Windows Data Protection API
4. **Rotation:** Update keys every 6 months or if exposed; rotate immediately after leak
5. **Auditing:** Log API key usage (without exposing the key) for anomaly detection

### Secrets in This Repository
- ✅ All secrets use environment variables or GitHub Secrets
- ✅ `.env.example` provided for reference (no actual secrets in repo)
- ✅ Pre-commit hook prevents accidental commits of `.env`
- ✅ GitHub Secret Scanning enabled to detect leaked credentials

---

## 🛡️ Network Security & External Connections

### Egress (Outbound) Connections
- **Football-Data.org API** (HTTPS) – Match data, competition info
- **API-Football (RapidAPI)** – Lineup, injury, statistics
- **Ball Don't Lie API** – NBA predictions (if enabled)
- **Open-Meteo API** – Weather data for match context
- **The Odds API** – Betting market odds and consensus
- **FBref.com / Understat.com** – xG and advanced stats (scraping if no API available)
- **SofaScore / FotMob** – Real-time lineups (if integrated)
- **GitHub** – Dependency fetching, workflow scheduling

### Ingress (Inbound) Connections
- ✅ **No public ports open** – This is a prediction engine, not a service with HTTP API (yet)
- ⚠️ **If deploying FastAPI server (future):** Must use HTTPS, rate-limiting, CORS policies, authentication

### Rate-Limiting & Throttling
All external API calls use `app/utils/http.safe_request_get()` with:
- Per-domain rate limits (see `config/settings.yaml`)
- Exponential backoff on 429 responses
- Connection timeout: 10 seconds
- Retry count: 3 (with backoff)

---

## 📋 Compliance & Audit Logging

### What Is Logged
- ✅ API request counts and response times (aggregated, not detailed)
- ✅ Data quality check results (passes/failures by source)
- ✅ Model retraining events and accuracy metrics
- ✅ Scheduled task execution logs (see `data/logs/daily/`)

### What Is NOT Logged
- ❌ API keys or authentication headers
- ❌ Full request/response bodies (only summary stats)
- ❌ Personal data or PII
- ❌ Sensitive configuration values

### Log Retention
- **Local:** 30 days (rotated by logrotate or cleanup script)
- **GitHub Actions:** 90 days (configurable)
- **Archived:** Critical events backed up to `data/backup_csv/` if needed

---

## 🔄 Release & Deployment Security

### Pre-Release Checklist
- [ ] All tests pass, including security tests (Bandit, SAST)
- [ ] Dependency scan passes (no unmitigated high/critical CVEs)
- [ ] No secrets in repo (Secret Scanning clean)
- [ ] Code review by maintainer
- [ ] CHANGELOG.md updated with breaking changes and security notes
- [ ] VULNERABILITY_ASSESSMENT.md reviewed and approved

### Versioning & Tagging
- **Semantic Versioning:** MAJOR.MINOR.PATCH (v4.1.0, v5.0.0, etc.)
- **Security patches:** Increment PATCH (v4.1.0 → v4.1.1)
- **Git signing:** Release tags signed with maintainer GPG key (optional, not currently enabled)

### Deployment Notifications
- GitHub Release notes include security fixes and any breaking changes
- Security advisories (if applicable) posted separately

---

## 📚 Related Security Documents

- [VULNERABILITY_ASSESSMENT.md](VULNERABILITY_ASSESSMENT.md) – Comprehensive audit results and public release decision
- [docs/SCRAPING_COMPLIANCE.md](docs/SCRAPING_COMPLIANCE.md) – Data collection legality and ethical guidelines
- [docs/ROTATE_KEYS_AND_SCRUB.md](docs/ROTATE_KEYS_AND_SCRUB.md) – Incident response: exposed API keys
- [.github/workflows/secret-scan.yml](.github/workflows/secret-scan.yml) – Automated secret detection CI job
- [.github/workflows/audit.yml](.github/workflows/audit.yml) – Dependency audit CI job
- [.env.example](.env.example) – Environment variable template

---

## ✅ Security Checklist

- [x] Threat model documented
- [x] Dependency scanning automated and running weekly
- [x] Secret management via environment variables
- [x] Data validation at ingestion points
- [x] SQL injection protections via ORM
- [x] Input validation via Pydantic
- [x] Rate-limiting for external API calls
- [x] Logging of sensitive fields redacted
- [x] HTTPS for all external connections (enforced by requests library)
- [x] Pre-commit hooks for secret detection
- [x] GitHub Secret Scanning enabled
- [ ] OWASP Top 10 review (if HTTP API deployed)
- [ ] Penetration testing (optional, for v6.0.0+)

---

**Status:** ✅ **SECURE FOR PUBLIC RELEASE** (pending VULNERABILITY_ASSESSMENT.md APPROVED decision)
