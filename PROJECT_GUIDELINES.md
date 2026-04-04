# PROJECT_GUIDELINES.md

This document defines the required files, structure, rules, and checks every repository must include to be professional, reproducible, secure, and recruiter-ready.

---

## Required top-level files and minimum contents

Each file below must exist at the repository root and include the listed elements.

### • README.md

- Title and one-line pitch.
- Badges: build, coverage, license, **Python version**. All four are required.
- GitHub repository **Topics/tags** set (minimum 5 relevant keywords for discoverability).
- Short description (2–4 sentences) describing scope and audience.
- Quickstart: Docker quickstart and local quickstart with exact commands and minimal prerequisites.
- Usage examples: one minimal command and one realistic workflow.
- Architecture overview: short paragraph, folder map, link to UML diagrams.
- MPDP summary: one-line link to MPDP.md and current milestone.
- Testing and quality: how to run tests, linters, and pre-commit hooks; CI badge and commands.
- Security: link to SECURITY.md and a short note about secrets handling.
- Contributing: link to CONTRIBUTING.md and a short summary of branch strategy and PR expectations.
- Changelog and releases: semantic versioning policy and link to CHANGELOG.md or Releases.
- License and contact: license name and maintainer contact.
- Claims rule: any performance or accuracy claim must state dataset, evaluation method, and baseline or be labeled as an internal experiment.

### • MPDP.md (Master Progress and Development Plan) — The living roadmap and canonical status document

- One-line project summary.
- Current milestone with status and dates.
- Milestone list with statuses and dates.
- Current sprint or focus.
- Next three actionable tasks with owners and acceptance criteria.
- Known risks and mitigations.
- Links to related issues and PRs.
- Update cadence: update at least once per milestone or sprint.

### • .gitignore

- Language- and environment-appropriate rules.
- Exclude venvs, compiled artifacts, IDE files, OS files, caches, large data, and secrets.
- If data is excluded, reference data/README.md.

### • LICENSE

- Full license text file.
- Reference license badge in README.md.

### • Dependency manifest and lock file

- Reproducible dependency declarations (e.g., requirements.txt + requirements-dev.txt or pyproject.toml + lock file).
- Pin or lock dependencies.
- Document exact command to recreate the environment.

### • Dockerfile and .dockerignore

- Dockerfile builds from repo root and produces a lean image.
- .dockerignore excludes local artifacts, venvs, and data.
- Docker quickstart documented in README.md.

### • SECURITY.md

- Contact for vulnerability reports and expected response time.
- Dependency update policy and whether automated scanning is enabled.
- Short threat model and mitigations.
- Secret handling and rotation instructions.

### • VULNERABILITY_ASSESSMENT.md

- Comprehensive security audit results before public release.
- Risk assessment: critical, high, medium, and low-risk findings (with none of critical/high required for release).
- Threat model coverage against common attacks (SQL injection, code execution, credential theft, etc.).
- Dependency vulnerability assessment (libraries, version requirements, known CVEs).
- Network security analysis (inbound/outbound connections, protocols, exposure).
- Data handling and privacy compliance review (PII, retention, deletion).
- Recommended security enhancements (prioritized by importance, blocking vs. optional).
- Public release decision: **APPROVED** or **BLOCKED** with justification.

### • AGENT_HANDOFF.md

- .env.example and instructions to populate environment variables.
- Secrets handling guidance and recommended secret stores.
- Devcontainer usage if present.
- Common development and test commands.
- Where to find datasets and how to obtain/regenerate them.
- How to retrain models and run evaluation.
- Troubleshooting tips and common failure modes.
- Goal: enable a new contributor to run the project in under 30 minutes.

### • SUPPORT.md (optional for open-source projects)

- Cryptocurrency donation options with wallet addresses (if applicable).
- Other ways to support (star, share, contribute, feedback).
- Explanation of what donations fund (development, security, documentation, etc.).
- Optional: sponsorship and recognition options.
- Optional: FAQ about support and donations.
- **Important:** README.md must link to SUPPORT.md rather than duplicating wallet addresses to avoid content drift.

### • UML/ and UML/README.md

- At least one component diagram and one sequence diagram (vector preferred).
- UML/README.md maps diagrams to code and runtime responsibilities.
- Diagrams updated when architecture changes.

### • architecture.md

- Textual system architecture: components, responsibilities, data flows, startup sequence, request lifecycle, background jobs, failure modes, and scaling considerations.
- Map architecture elements to folders and runtime responsibilities.

### • Standard directories and files

- **tests/** — unit, integration, and smoke tests; use fixtures and small sample datasets for CI.
- **docs/** — comprehensive documentation and guides.
- **scripts/** — idempotent, documented scripts with --help.
- **data/** — data/README.md explains expected files, formats, and retrieval or regeneration steps.
- **deploy/** — staging and production artifacts with clear instructions.
- **.github/workflows/** — CI templates covering tests, linting, type checks, and release automation.
- **CODE_OF_CONDUCT.md** — community conduct guidelines.
- **CONTRIBUTING.md** — contributor workflow and expectations.
- **CHANGELOG.md** — semantic versioning policy and release history.
- **CODEOWNERS** — file ownership and required reviewers.
- **THIRD_PARTY_NOTICES.md** — attribution for third-party libraries.
- **MAINTAINERS.md** — active maintainers and their responsibilities.
- **SUPPORT.md** — donation and support contribution methods (optional for open-source projects).
- **DATA_LICENSE.md / PRIVACY.md** — data-specific licensing and privacy policies (if applicable).
- **MODEL_CARD.md / DATA_CARD.md** — model or dataset documentation (if applicable).
- **USER_MANUAL.md** — step-by-step end-user guide with examples and screenshots (required for applications with user-facing interfaces; optional for libraries).
- **`.github/dependabot.yml`** — automated dependency updates (required; weekly pip + monthly Actions).
- **`docs/api/`** — auto-generated API docs via Sphinx or MkDocs (required for library projects; optional for apps).

---

## README structure (ordered, no repetition)

Follow this exact order to keep repositories predictable:

1. Title and one-line pitch
2. Badges for build, coverage, license, and Python version
3. Short description (2–4 sentences)
4. Quickstart: Docker and local quickstart with exact commands
5. Usage examples: minimal command and realistic workflow
6. Architecture overview: paragraph, folder map, link to UML
7. MPDP summary: link and current milestone
8. Testing and quality: how to run tests, linters, pre-commit hooks; CI badge
9. Security: link to SECURITY.md and secrets note
10. Contributing: link and branch/PR expectations
11. Support (optional for open-source projects): brief description with link to SUPPORT.md for full donation options and contribution methods
12. Changelog and releases: semantic versioning policy and link
13. License and maintainer contact
14. Claims rule reminder

---

## Version control, CI, and pre-publish checklist

### Branch strategy

- **Branch protection:** protect main (or stable); require PR reviews and green CI.
- **Branch naming:** feature/, hotfix/, optional develop for larger teams.
- **Commit messages:** imperative mood, concise subject, reference issue/MPDP IDs.

### Pull request workflow

- **PR checklist:** link to issue/MPDP task; include tests or justify omission; pass linters and type checks; update docs if behavior changed; at least one reviewer.

### CI pipeline

- **Scope:** run on PRs and main.
- **Steps:** dependency install, linting, type checking, tests, Docker build.
- **Fail fast:** critical errors must block merge.

### Code quality

- **Pre-commit hooks:** require formatting, import sorting, linter, and dependency safety scanner.
- **Coverage target:** aim for at least 70% on core modules (80%+ ideal); document exceptions in MPDP.md.
- **Test artifacts:** produce JUnit XML and coverage reports; store artifacts in CI for historical comparison.
- **No print() in library code:** use the standard `logging` module with module-level loggers. `print()` is only acceptable in CLI entry points and top-level scripts. Audit all source files before public release.
- **Version sync:** version in `pyproject.toml` (or `setup.cfg`) must always match the latest git tag and CHANGELOG entry. Verify before tagging a release.

### Code documentation

- **Module-level docstrings:** Each module should have a docstring describing its purpose, key classes/functions, and usage example.
- **Function/method docstrings:** Include parameter types, return types, and expected behavior; use language-standard format (Python: Google/NumPy style recommended).
- **Class docstrings:** Describe purpose, public interface, and initialization requirements.
- **Type hints:** Use full type annotations for public APIs (Python 3.7+); document complex types.
- **Inline comments:** Only for non-obvious logic; prefer readable code over comments.
- **Disable comments must explain why:** All "# TODO", "# FIXME", "# HACK" must reference an issue or MPDP task ID.

### Pre-publish checklist (must pass before public release)

- README quickstart works in under 10 minutes.
- MPDP.md lists next three tasks with owners and criteria.
- Tests pass locally and in CI.
- No secrets in repo; use .env.example for reference.
- Docker build succeeds.
- UML diagrams present (component and sequence).
- LICENSE file correct and badge in README.
- CHANGELOG.md or Releases documented.
- SECURITY.md present and complete.
- VULNERABILITY_ASSESSMENT.md completed and approved for public release.
- All required files listed in this document are present.
- README has all four badges: build, coverage, Python version, license.
- GitHub repository Topics/tags set (minimum 5 relevant keywords).
- `.github/dependabot.yml` present and configured.
- No `print()` statements in library/package source code — replaced with `logging`.
- `pyproject.toml` version matches latest git tag and CHANGELOG entry.
- GitHub Release created from the version tag with release notes.

---

## Enforcement and automation

- **Location:** Place PROJECT_GUIDELINES.md at the repository root.
- **PR template:** Add a PR template (.github/pull_request_template.md) that references the pre-publish checklist and requires confirmation of checklist items before merging.
- **Automated checks:** Verify presence of required files, run tests, run linters, and build Docker images in CI.
- **Living documents:** Keep MPDP.md and README.md up to date; treat MPDP.md as canonical project status.

---

## Agent Implementation Guide

This section provides explicit instructions for AI agents implementing this template in a new or existing repository.

### Overview

**Goal:** Establish a professional, reproducible, governance-aligned repository with all required files present and compliant before public release.

**Success Criteria:** All 24 Tier 1 + Tier 2 items checked ✅, pre-publish checklist fully passed, and CI green.

**Estimated effort:** 3–5 days for a new repo; 2–3 days for restructuring existing code.

### Phase-Based Implementation (Do in Order)

#### Phase 1: Foundation & Runnable (Day 1–2)

**Blocking:** Nothing ships without these.

1. **Copy PROJECT_GUIDELINES.md** to repo root (customize inapplicable items)
2. **Create/update README.md** — Ensure quickstart (Docker + local) works in < 10 minutes
3. **Create/update .gitignore** — Exclude venvs, caches, secrets, large data
4. **Create/update LICENSE** — Full license text + badge in README
5. **Create/update Dependency manifest** (requirements.txt + lock OR pyproject.toml)
   - **Version sync rule:** ensure version in `pyproject.toml` matches the intended release tag before committing
6. **Create/update Dockerfile + .dockerignore** — Builds lean image from repo root
7. **Create/update tests/** — Add sample unit tests (even if minimal) to validate structure
8. **Create .github/workflows/ci.yml** — Basic pipeline: install, lint, test, Docker build
9. **Validate:** README quickstart works; tests run locally; Docker builds

#### Phase 2: Governance & Safety (Day 2–3)

**Blocking for public release:**

1. **Create SECURITY.md** — Threat model, dependency policy, secret handling, contact info
2. **Create CONTRIBUTING.md** — Branch strategy, commit style, PR checklist, code standards
3. **Create CODE_OF_CONDUCT.md** — Community guidelines (copy Contributor Covenant 2.1 if needed)
4. **Create CODEOWNERS** — Assign code review ownership (GitHub auto-assignment)
5. **Create CHANGELOG.md** — Semantic versioning policy + current release notes
6. **Create THIRD_PARTY_NOTICES.md** — Attribution for all open-source dependencies
7. **Create MAINTAINERS.md** — Contact, decision process, approval authority
8. **Create `.github/dependabot.yml`** — Weekly pip updates + monthly GitHub Actions updates
9. **Create .github/pull_request_template.md** — Checklist linking to pre-publish requirements
10. **Create .github/FUNDING.yml** (optional) — Custom donation links or GitHub Sponsors
11. **Validate:** All files exist, CI runs green, no broken links in docs

#### Phase 3: Architecture & Onboarding (Day 4–5)

**Required before claiming "production-ready":**

1. **Create UML/ with diagrams** — At least 1 component diagram + 1 sequence diagram (SVG preferred)
2. **Create UML/README.md** — Map diagrams to code folders and runtime flow
3. **Create architecture.md** — System components, data flows, startup, failure modes, scaling
4. **Create AGENT_HANDOFF.md** — Dev setup commands, .env.example, datasets, troubleshooting (< 30 min setup goal)
5. **Create MPDP.md** — Project summary, current milestone, next 3 tasks with criteria
6. **Create docs/** — Comprehensive guides (if not already present)
7. **Validate:** All architecture docs linked in README; "under 30 min" setup verified by test run

**Release blocker — must pass all checks:**

1. **Audit for print() statements** — Search all source files; replace with `logging` calls; `print()` only allowed in CLI entry points
2. **Verify version sync** — `pyproject.toml` version == latest git tag == CHANGELOG section heading
3. **Set GitHub repository Topics** — Minimum 5 relevant keywords (language, domain, framework)
4. **Verify README badges** — Build, coverage, Python version, license badges all present and rendering
5. **Create VULNERABILITY_ASSESSMENT.md** — Security audit (see template in Tier 1 section)
6. **Run pre-publish checklist** — All 17 items checked
7. **Verify CI green** — All tests, linters (black, ruff, mypy), security scans (bandit, safety) pass
8. **Create GitHub Release** from version tag with full release notes
9. **Decision:** Mark APPROVED (public release ready) or BLOCKED (fix issues first)
10. **Validate:** All 24 items checked; compliance counter at 24/24

### Priority & Blocking Rules

| Item | Phase | Blocking | Why |
| --- | --- | --- | --- |
| README.md | 1 | Yes | Must be discoverable and runnable |
| tests/ | 1 | Yes | Must validate code integrity |
| CI pipeline | 1 | Yes | Must gate all commits |
| SECURITY.md | 2 | Yes (public release) | Required before public visibility |
| VULNERABILITY_ASSESSMENT.md | 4 | Yes (public release) | Release approval gate |
| UML diagrams | 3 | No (but recommended) | Aids contributor onboarding |
| PRIVACY.md | — | No (optional) | Only if handling PII |
| MODEL_CARD.md | — | No (optional) | Only if publishing ML models |

### Key Commands & Templates

**When implementing, agents should reference or use these patterns:**

```bash
# Initialize repository structure
mkdir -p tests/ docs/ scripts/ data/ src/ .github/workflows UML

# Create Python dependencies (example)
pip freeze > requirements.txt
pip install pytest pytest-cov black ruff mypy bandit

# Run initial CI locally
pytest tests/ --cov=src --cov-fail-under=70
black . --check
ruff check .
mypy src/
bandit -r src/

# Create Docker image
docker build -t <project>:<version> .
docker run --rm <project>:<version> python -m pytest tests/

# Git setup
git config user.email "your@email.com"
git config user.name "Your Name"
git add .
git commit -m "chore: Initialize repository with PROJECT_GUIDELINES"
git tag v0.1.0
git push origin main --tags
```

### Tracking Progress

As each file is created:

1. **Update the "Implementation Status" checklist** in PROJECT_GUIDELINES.md
2. **Commit with semantic message:** `chore: Add README.md` or `docs: Add architecture.md`
3. **Run CI and verify no new failures**
4. **Mark in compliance counter:** (__/24 at bottom)

### Validation Checklist for Agents

Before declaring a repository "production-ready," verify:

- [ ] All 24 Tier 1 + Tier 2 items exist and are non-empty
- [ ] CI pipeline runs green on all commits
- [ ] README quickstart works in < 10 minutes (test it yourself)
- [ ] README has all four badges: build, coverage, Python version, license
- [ ] GitHub repository Topics/tags set (minimum 5 keywords)
- [ ] No hardcoded secrets (search for passwords, API keys, tokens)
- [ ] No `print()` in library source code — all replaced with `logging`
- [ ] Docker image builds and runs successfully
- [ ] Tests achieve >= 70% coverage on core modules
- [ ] UML diagrams are present and linked in README
- [ ] VULNERABILITY_ASSESSMENT.md decision: **APPROVED**
- [ ] All links in documentation are valid (no 404s)
- [ ] MPDP.md has current milestone + next 3 tasks
- [ ] CODEOWNERS file assigns reviewers correctly
- [ ] CHANGELOG.md documents current release with semantic version
- [ ] `pyproject.toml` version matches git tag and CHANGELOG heading
- [ ] `.github/dependabot.yml` present and configured
- [ ] GitHub Release created from version tag with release notes

### When Items Don't Apply

For some repositories, certain items may not apply (e.g., no ML model → skip MODEL_CARD.md). **In those cases:**

1. **Document the exemption** in the "Optional Files" section at bottom of PROJECT_GUIDELINES.md
2. **Example:**

   ```markdown
   ### Optional Files
   
   - **MODEL_CARD.md** — Not applicable (no ML models in this project)
   - **PRIVACY.md** — Not applicable (no personal data collected)
   - **deploy/** — Not applicable (library-only, no deployment artifacts)
   ```

3. **Do not check them** in the compliance counter; adjust total downward
4. **Justify briefly** so future maintainers understand the decision

### Troubleshooting for Agents

| Problem | Solution |
| --- | --- |
| Tests fail on import | Check .github/workflows/ci.yml installs dependencies first (`pip install -e .`) |
| Docker build fails | Verify .dockerignore excludes venvs, caches; check Dockerfile inherits from supported base image |
| CI coverage below threshold | Lower coverage target in MPDP.md (document why), or add missing test cases |
| UML diagrams won't render | Save as SVG or PNG; keep PlantUML source in UML/ folder |
| README links broken | Check relative paths; use absolute GitHub URLs for reference to branches/releases |
| Secrets detected in commits | Use `git rm --cached` to remove; add to .gitignore; regenerate any exposed tokens |

---

## Implementation Status (v4.1.0)

### Project Compliance

✅ **Status:** All 24 required files present and in compliance. Repository approved for public release.

#### Tier 1: Critical Documentation

- [x] README.md
- [x] MPDP.md
- [x] .gitignore
- [x] LICENSE
- [x] Dependency manifest and lock file
- [x] Dockerfile and .dockerignore
- [x] SECURITY.md
- [x] VULNERABILITY_ASSESSMENT.md
- [x] AGENT_HANDOFF.md
- [x] UML/ and UML/README.md
- [x] architecture.md
- [x] .github/workflows/
- [x] CONTRIBUTING.md

#### Tier 2: Governance & Community Files

- [x] CODE_OF_CONDUCT.md
- [x] CHANGELOG.md
- [x] THIRD_PARTY_NOTICES.md
- [x] MAINTAINERS.md
- [x] CODEOWNERS
- [x] .github/dependabot.yml

#### Standard Directories

- [x] tests/
- [x] docs/
- [x] scripts/
- [x] data/
- [x] src/

**Total Compliance:** ✅ 24/24 required files present

### Optional Files

- [x] USER_MANUAL.md — Created for end-users (application with user-facing CLI and reports)
- [x] deploy/ — Present (deploy/ folder with deployment scripts for Windows task scheduling)
- [ ] MODEL_CARD.md / DATA_CARD.md — Not applicable (uses external data sources, not publishing proprietary models)
- [ ] PRIVACY.md / DATA_LICENSE.md — Not applicable (no personal data collected; external data sources have own licensing)
- [ ] docs/api/ (Sphinx/MkDocs) — Not applicable (CLI application, not library; inline docs sufficient)

---

## Quick editorial notes for maintainers

- **Clarity:** Use short, imperative sentences so checklist items can be validated by scripts.
- **Diagrams:** Prefer vector UML diagrams (SVG) and keep source files (e.g., PlantUML) in UML/.
- **Handoff:** Make AGENT_HANDOFF.md a runnable checklist: include exact commands, example .env values (no secrets), and a minimal troubleshooting section.
- **Precision:** Replace vague phrasing with explicit deliverables and measurable cadence (e.g., "update at least once per milestone or sprint").

---

**Last updated:** 2026-04-04
