# CONTRIBUTING.md

Thank you for your interest in contributing to **SportsPredictionSystem**! This document outlines the guidelines and workflow for contributing code, documentation, and improvements.

---

## 📋 Code of Conduct

This project is committed to providing a welcoming and inspiring community. Please read and follow our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) in all interactions.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9 or higher
- Git and GitHub account
- Familiarity with the [AGENT_HANDOFF.md](AGENT_HANDOFF.md) onboarding guide (required)
- Read [SECURITY.md](SECURITY.md) if working on data/API integrations

### Quick Setup (30 minutes)
Follow [AGENT_HANDOFF.md](AGENT_HANDOFF.md) for complete setup instructions. TL;DR:

```bash
# Clone, setup venv, install dependencies
git clone https://github.com/Zed-777/sports-prediction-system.git
cd sports-prediction-system
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt

# Verify setup
python phase2_lite.py
pytest -q
```

---

## 🔄 Branch Strategy

### Main Branch
- **`main`** — Production-ready code
  - **Protected:** Requires PR review + green CI
  - **Deployment:** Automatic on merge (if CI/CD configured)
  - **Policy:** Only merge stable, tested code

### Feature & Bugfix Branches
Follow this naming convention:

```text
feature/<issue-id>-<short-description>
  Example: feature/DQ-001-lineup-confirmation

hotfix/<issue-id>-<short-description>
  Example: hotfix/#123-api-key-leak

docs/<short-description>
  Example: docs/architecture-diagrams

refactor/<short-description>
  Example: refactor/feature-pipeline-performance
```

### Branch Creation & Updates

```bash
# Create a new feature branch from main
git checkout main
git pull origin main
git checkout -b feature/DQ-001-lineup-confirmation

# Make changes, test, commit
git add .
git commit -m "feat: Implement real-time lineup confirmation connector"

# Push to GitHub
git push origin feature/DQ-001-lineup-confirmation

# Create Pull Request (link to issue or MPDP.md task)
# → Go to GitHub and open PR from your branch to main
```

**Keep branches up-to-date:**

```bash
git fetch origin
git rebase origin/main
git push --force-with-lease
```

---

## 💬 Commit Messages

Follow **Conventional Commits** format for clarity and automated changelog generation:

```text
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat:` — New feature or capability
- `fix:` — Bug fix
- `docs:` — Documentation only (README, guides, comments)
- `style:` — Code formatting (black, ruff, no logic change)
- `refactor:` — Code restructuring (no new features, no bug fixes)
- `perf:` — Performance improvement
- `test:` — Tests or test fixtures
- `chore:` — Tooling, CI, dependency updates
- `ci:` — CI/CD workflow changes

### Scope (optional)
- `data:` — Data ingestion, API connectors
- `features:` — Feature engineering
- `models:` — ML model changes
- `reports:` — Report generation
- `infra:` — Infrastructure, deployment
- `tests:` — Test suite
- `docs:` — Documentation

### Examples

```bash
git commit -m "feat(data): Add FBref xG connector with caching"
git commit -m "fix(models): Correct ELO recency decay formula"
git commit -m "docs: Update AGENT_HANDOFF.md with troubleshooting"
git commit -m "perf(features): Vectorize form metric calculations"
git commit -m "test(models): Add uncertainty quantification tests"
```

### Reference Issues & Tasks
Link your commits to issues or MPDP.md tasks:

```bash
# Format: <type>(<scope>): <subject> (#<issue-id> or references <task-id>)
git commit -m "feat(data): Add lineup connector (DQ-001)"
git commit -m "fix(models): Ensemble disagreement penalty (#45)"
```

---

## 🧪 Testing & Code Quality

### Testing Requirements
- ✅ **Required:** All new code must include unit tests
- ✅ **Required:** Tests must pass locally before push
- ✅ **Expected:** ≥70% code coverage on modified modules (core modules: ≥80%)
- ✅ **Optional but encouraged:** Integration tests for complex workflows

### Run Tests Locally

```bash
# Quick test (fast feedback)
pytest tests/ -q

# Full test with coverage
pytest tests/ --cov=app --cov-fail-under=70

# Test specific module
pytest tests/test_models.py -v

# Test with detailed output
pytest tests/ -v --tb=short
```

### Code Quality Checklist

Before pushing, run:

```bash
# 1. Format code with black
black app/ scripts/ tests/

# 2. Lint with ruff
ruff check app/ scripts/ tests/
ruff check --fix app/  # Auto-fix where possible

# 3. Type checking with mypy
mypy app/ --strict

# 4. Run tests
pytest tests/ --cov=app --cov-fail-under=70

# 5. Security scan with bandit
bandit -r app/
```

**Or run all at once:**

```bash
# One-liner for complete quality check
black . && ruff check . && mypy app/ && pytest tests/ --cov=app && bandit -r app/
```

### CI/CD Pipeline
The following checks run automatically on every PR:

- ✅ **Linting:** black, ruff
- ✅ **Type checking:** mypy
- ✅ **Tests:** pytest with coverage report
- ✅ **Security:** bandit, safety, pip-audit
- ✅ **Docker build:** Dockerfile builds successfully
- ✅ **Dependency audit:** No unmitigated CVEs

**Your PR cannot merge if:**
- Tests fail
- Coverage drops below 70%
- Linter/type checker errors present
- Security scan finds critical issues

---

## 📝 Pull Request Workflow

### PR Description Template

Use the GitHub PR template (`.github/pull_request_template.md`):

```markdown
## Description
Brief summary of what this PR does.

## Related Issue
Closes #123 or references MPDP.md task DQ-001

## Type of Change
- [x] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation

## Testing
- [ ] Added/updated unit tests
- [ ] Added/updated integration tests
- [ ] Tested locally with: [describe setup]
- [ ] Coverage: [include screenshot or percentage]

## Code Quality
- [ ] Passes `black`, `ruff`, `mypy`
- [ ] No new warnings or errors
- [ ] Added docstrings for public APIs
- [ ] Updated README.md if behavior changed
- [ ] Updated CHANGELOG.md

## Pre-Publish Checklist (if release-ready)
- [ ] SECURITY.md reviewed (if data/API changes)
- [ ] No hardcoded secrets in code
- [ ] Performance impact assessed
- [ ] Backward compatibility verified
```

### PR Review Process

1. **Author:** Push feature branch and open PR
2. **CI/CD:** Automated checks run (tests, linting, security)
3. **Reviewer(s):** @Zed-777 (maintainer) or assigned reviewers
4. **Review:** Code style, logic, tests, documentation
5. **Approval:** "Approve" or request changes
6. **Merge:** Squash & merge to main (preserves commit message)

**Review expectations:**
- Constructive feedback focused on code quality
- Response time: Within 48 hours for PRs
- Accessibility: Ask questions if code is unclear

### Merging

```bash
# Maintainer: Merge via GitHub (Squash & merge recommended)
# → Squash consolidates feature branch into one clean commit
# → Example: "feat(data): Add real-time lineup confirmation (DQ-001)"

# Or merge locally if required:
git checkout main
git pull origin main
git merge --no-ff feature/DQ-001-lineup-confirmation
git push origin main
```

---

## 📚 Documentation Standards

### Docstrings (Python)

Use **Google style** docstrings:

```python
def predict_match(match_id: int, league: str) -> Dict[str, float]:
    """Predict match outcome using ensemble models.

    Args:
        match_id: Unique identifier for the match.
        league: League code (e.g., 'la-liga', 'premier-league').

    Returns:
        Dictionary with keys:
            - 'home': Probability home team wins (0.0-1.0)
            - 'draw': Probability match is draw (0.0-1.0)
            - 'away': Probability away team wins (0.0-1.0)
            - 'confidence': Confidence in prediction (0.3-0.95)

    Raises:
        ValueError: If match_id not found in database.
        APIError: If external API call fails.

    Example:
        >>> pred = predict_match(12345, 'la-liga')
        >>> print(f"Home win prob: {pred['home']:.2%}")
        Home win prob: 55.32%
    """
    ...
```

### Module Docstrings

Start each module with a docstring:

```python
"""Enhanced data ingestion pipeline for sports prediction.

This module orchestrates data fetching from multiple external APIs,
validation, quality checks, and caching. It is the entry point for
all data acquisition workflows.

Key classes:
    - DataIngestionOrchestrator: Main coordinator
    - FootballDataConnector: Football-Data.org client
    - APIFootballConnector: RapidAPI API-Football client

Example:
    >>> orchestrator = DataIngestionOrchestrator()
    >>> matches = orchestrator.fetch_upcoming_matches(league='la-liga')
    >>> validated = orchestrator.validate_and_cache(matches)
"""
```

### Type Hints

Use full type annotations for public APIs:

```python
from typing import Dict, List, Optional, Tuple

def train_model(
    features: np.ndarray,
    labels: np.ndarray,
    epochs: int = 100,
    learning_rate: float = 0.01,
) -> Tuple[Model, Dict[str, float]]:
    """Train ML model on features and labels.

    Args:
        features: Training data array (n_samples, n_features).
        labels: Target labels (n_samples,).
        epochs: Number of training iterations.
        learning_rate: Optimization learning rate.

    Returns:
        Tuple of:
            - Trained Model object
            - Metrics dict: {'acc': 0.85, 'loss': 0.12, ...}
    """
    ...
```

### Comments

- Prefer **readable code** over comments
- Document **non-obvious logic** only
- Every `# TODO`, `# FIXME`, `# HACK` must reference an issue:

```python
# ✅ GOOD: References issue ID
# TODO (#123): Implement xG feature after API available

# ❌ BAD: No reference
# TODO: Fix this later

# ✅ GOOD: Explains why
# Using cache here because API rate-limited to 10 req/min
cached_result = cache.get(match_id)

# ❌ BAD: Explains obvious code
x = x + 1  # Increment x
```

### README & Documentation

- Keep README.md **up-to-date** with quickstart and examples
- Add `.md` files to `docs/` for detailed guides
- Link all documentation from README or CONTRIBUTING.md
- Use **exact command examples** (copy-paste ready)

---

## 🔐 Security & Secrets Handling

### API Keys & Secrets

- ✅ **Always** use environment variables (loaded from `.env`)
- ✅ **Never** hardcode API keys in source code
- ✅ **Copy** `.env.example` for reference; actual `.env` in `.gitignore`
- ✅ **Rotate** API keys if exposed or annually

### Pre-Commit Checks

Before pushing, verify:

```bash
# Check for accidental secrets
git diff HEAD | grep -i "api_key\|password\|token\|secret"
# If found: Remove and amend commit before push

# Verify .env not staged
git status | grep .env
# Should show: ".env" (not staged)
```

### Data Collection & APIs

When adding new data sources:
1. **Read [SCRAPING_COMPLIANCE.md](docs/SCRAPING_COMPLIANCE.md)** — Legal guidelines
2. **Check robots.txt** — Must respect site's crawl policy
3. **Review Terms of Service** — Must not violate API ToS
4. **Document source** — Include provenance and rate limits
5. **Add tests** — Mock external API in tests; use small fixtures

Example (new API connector):

```python
"""Connector for Example Sports API.

Legal review: Checked robots.txt on 2026-04-03; requests 100/hour allowed.
ToS: Commercial use permitted with proper attribution.
Rate limit: 100 requests per hour (enforced in config/settings.yaml).
"""

class ExampleSportsConnector:
    """Fetch data from Example Sports API.
    
    Implements polite rate-limiting per docs/SCRAPING_COMPLIANCE.md.
    """
    
    BASE_URL = "https://api.example-sports.com/v1"
    RATE_LIMIT = 100  # requests per hour
    
    def __init__(self):
        self.key = os.getenv("EXAMPLE_SPORTS_KEY")
        # ... initialize with rate limiting
```

---

## 🎯 Working on Specific Tasks

### Task: New Feature (`feature/*` branch)

**Example:** Implementing real-time lineup confirmation (DQ-001)

```bash
# 1. Create branch from MPDP.md task ID
git checkout -b feature/DQ-001-lineup-confirmation

# 2. Implement in appropriate module
#    - New connector: app/data/connectors/lineups.py
#    - Test fixtures: tests/test_lineups.py
#    - Configuration: config/settings.yaml (rate limits)

# 3. Write tests (required)
pytest tests/test_lineups.py -v

# 4. Update documentation
#    - docs/data-sources.md (new source added)
#    - CHANGELOG.md ([Unreleased] / Added section)
#    - README.md (if user-facing)

# 5. Code quality checks
black app/ scripts/ tests/
ruff check . && mypy app/ && pytest tests/ --cov=app

# 6. Create PR with reference to task
git push origin feature/DQ-001-lineup-confirmation
# → GitHub: Create PR, link to MPDP.md or issue
```

### Task: Bug Fix (`hotfix/*` branch)

**Example:** Fixing ELO recency decay formula

```bash
# 1. Create branch from issue ID
git checkout -b hotfix/#123-elo-decay-formula

# 2. Fix code + add unit test for regression
#    - File: app/models/elo_model.py
#    - Test: tests/test_models.py::test_elo_recency_decay()

# 3. Verify fix
pytest tests/test_models.py::test_elo_recency_decay -v

# 4. Update CHANGELOG.md
#    [Unreleased] / Fixed section

# 5. Code quality
ruff check . && pytest tests/ --cov=app

# 6. Push & PR
git push origin hotfix/#123-elo-decay-formula
```

### Task: Documentation (`docs/*` branch)

```bash
# 1. Create branch
git checkout -b docs/architecture-diagrams

# 2. Add/update `.md` files
#    - UML/README.md (diagram explanation)
#    - docs/architecture.md (textual design)

# 3. Check links
grep -r "\[.*\](.*\.md)" docs/ UML/
# Verify all .md files exist

# 4. Commit and push
git push origin docs/architecture-diagrams

# 5. PR (no CI checks needed, documentation only)
```

---

## 🏆 Best Practices

### Code Organization
- **Keep modules focused** — One responsibility per file
- **Use type hints** — Helps catch bugs and improves readability
- **Avoid deep nesting** — Limit to 2–3 levels max
- **DRY principle** — Don't Repeat Yourself; extract shared functions

### Testing
- **Test behavior, not implementation** — Assert outcomes, not internal state
- **Use fixtures for data** — `tests/data/` folder for sample files
- **Mock external APIs** — Don't call real APIs in tests
- **Parameterize tests** — Use `@pytest.mark.parametrize` for multiple inputs

### Performance
- **Profile before optimizing** — Use `cProfile`; identify real bottlenecks
- **Batch operations** — Process in chunks to avoid memory issues
- **Cache expensive operations** — xG calculations, ELO ratings
- **Monitor latency** — Log timing in hot paths; alert if >3s per match

### Data Quality
- **Validate at ingestion** — Use Pydantic; fail fast on bad data
- **Cross-validate sources** — Compare 2+ APIs; flag discrepancies
- **Version data snapshots** — `data/snapshots/` for reproducibility
- **Document data lineage** — Include `provenance` field in all data

---

## 🚨 Reporting Issues

Found a bug? Have a feature request? Please **open a GitHub issue**:

1. **Search existing issues** — Avoid duplicates
2. **Use issue template** — Fill in title, description, expected behavior, actual behavior
3. **Attach screenshots/logs** — Help us reproduce
4. **Reference related issues** — "See also #123"

### Security Issues

**Do NOT create a public issue for security vulnerabilities.** Email [maintainer@sports-prediction-system.local] instead.

See [SECURITY.md](SECURITY.md) for full disclosure policy.

---

## 📞 Getting Help

- **Onboarding:** See [AGENT_HANDOFF.md](AGENT_HANDOFF.md)
- **Architecture:** See [architecture.md](architecture.md) and [UML/README.md](UML/README.md)
- **Project roadmap:** See [MPDP.md](MPDP.md)
- **Coding standards:** See `.github/copilot-instructions.md`
- **Data collection:** See [docs/SCRAPING_COMPLIANCE.md](docs/SCRAPING_COMPLIANCE.md)
- **Security:** See [SECURITY.md](SECURITY.md)

**Questions?** Open a GitHub Discussion or ping @Zed-777.

---

## ✅ Pre-Merge Checklist (for Maintainer)

Before merging a PR:

- [ ] Passes all CI checks (tests, linting, type checking, security)
- [ ] Code review approved by at least 1 maintainer
- [ ] Coverage didn't decrease (or justified in PR)
- [ ] CHANGELOG.md updated (if user-facing changes)
- [ ] README.md updated (if new feature)
- [ ] No secrets or hardcoded values
- [ ] Commit message follows Conventional Commits format
- [ ] Squash & merge to main (keeps history clean)

---

## 📖 References

- [PROJECT_GUIDELINES.md](PROJECT_GUIDELINES.md) — Repository standards
- [AGENT_HANDOFF.md](AGENT_HANDOFF.md) — Developer onboarding
- [SECURITY.md](SECURITY.md) — Security policies
- [MPDP.md](MPDP.md) — Roadmap and current milestone
- [architecture.md](architecture.md) — System design
- [UML/README.md](UML/README.md) — Architecture diagrams

---

## Thank you for contributing! 🎉

Your work helps make SportsPredictionSystem better for everyone. Looking forward to your PRs!

---

**Last Updated:** 2026-04-03  
**Maintained by:** @Zed-777
