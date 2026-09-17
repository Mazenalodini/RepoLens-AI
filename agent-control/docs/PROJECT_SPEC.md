# RepoLens AI
## Product & Engineering Specification

**Version:** 1.0
**Status:** MVP Baseline
**Primary Product Input:** GitHub Repository URL
**Development Environment:** Windows
**Primary Language:** Python

---

# 1. Product Identity

**Name:** RepoLens AI

**Full Name:** AI-Powered GitHub Repository Intelligence & Engineering Health Platform

**Tagline:** Understand. Analyze. Improve.

---

# 2. Product Vision

RepoLens AI is a platform for understanding and evaluating software repositories.

The user provides a GitHub repository URL. RepoLens acquires the repository in a controlled workspace, gathers objective evidence about the repository, performs deterministic analysis, normalizes results into structured Findings, then uses AI to interpret those findings and generate a professional engineering report.

The product is not intended to be a generic chatbot.

Its defining principle is:

> **Evidence First, AI-Assisted.**

---

# 3. Problem

Software repositories spread important engineering information across source files, configuration, tests, documentation, dependency manifests, and Git history.

Manual assessment can require substantial time.

RepoLens AI reduces this effort by consolidating repository evidence and converting it into:

- structured observations
- engineering findings
- AI-assisted explanations
- actionable recommendations
- professional reports

---

# 4. Primary User Journey

```text
GitHub Repository URL
        ↓
Validate
        ↓
Acquire Repository
        ↓
Create Controlled Workspace
        ↓
Discover Repository
        ↓
Run Analyzers
        ↓
Collect Evidence
        ↓
Generate Findings
        ↓
Build AI Context
        ↓
Generate AI Engineering Review
        ↓
Generate Report
```

---

# 5. MVP

The MVP must demonstrate a complete end-to-end path:

```text
GitHub URL
→ Acquisition
→ Discovery
→ Language Detection
→ Structure Analysis
→ Basic Code Quality Analysis
→ Git Analysis
→ Documentation Analysis
→ Dependency Analysis
→ Findings
→ AI Interpretation
→ HTML Report
```

The MVP should favor working end-to-end functionality over a large number of incomplete features.

---

# 6. Analysis Domains

## Repository Discovery

Collect:

- file counts
- directory structure
- file types
- source files
- configuration files
- test indicators
- documentation indicators
- entry-point candidates
- repository metadata

## Language Detection

Detect languages from repository evidence.

Distinguish detection from inference.

## Architecture Analysis

Analyze:

- module structure
- directory organization
- dependency relationships where practical
- responsibility boundaries
- architectural signals

Architecture interpretation must remain evidence-backed.

## Code Quality

Potential signals:

- long functions
- large classes
- excessive complexity
- deep nesting
- excessive parameters
- repeated logic indicators
- naming issues
- magic values
- dead-code indicators
- large modules

Actual metrics must come from deterministic measurements or tools.

## Testing

Detect:

- test files
- test directories
- test frameworks
- test configuration
- optional explicit test execution

Never invent coverage or execution results.

## Git

Inspect:

- Git repository presence
- branches
- tags
- commits
- .gitignore
- activity signals
- repository hygiene

## Documentation

Inspect:

- README
- docs/
- CONTRIBUTING
- CHANGELOG
- LICENSE
- setup/usage documentation

## Dependencies

Inspect common manifests such as:

- requirements.txt
- pyproject.toml
- package.json

Do not claim vulnerabilities without a real vulnerability source.

## Security Hygiene

Detect signals such as:

- environment files
- credential-like filenames
- key-like files
- large generated artifacts
- suspicious repository hygiene

Never unnecessarily send secrets to AI.

---

# 7. Findings

A Finding should conceptually include:

- id
- category
- severity
- title
- description
- evidence
- source analyzer
- file/location
- recommendation
- metadata

Categories:

- repository
- architecture
- code_quality
- testing
- git
- documentation
- dependency
- security_hygiene

Severity:

- Critical
- High
- Medium
- Low
- Info

Severity should be deterministic and explainable.

---

# 8. AI Responsibilities

AI may:

- summarize
- explain
- correlate
- contextualize
- generate recommendations
- produce executive summaries

AI must not invent:

- metrics
- tests
- vulnerabilities
- file locations
- repository structure
- facts not present in Evidence

---

# 9. AI Provider

The system should expose an `AIProvider` abstraction.

The MVP may implement one provider.

Future providers may include:

- OpenAI
- Anthropic
- Google
- local models

Provider-specific logic must remain outside domain logic.

---

# 10. Reports

MVP report formats:

- HTML
- JSON
- Markdown

PDF is a post-MVP extension unless implementation remains safely within schedule.

Report sections:

1. Executive Summary
2. Repository Overview
3. Technology Stack
4. Project Structure
5. Architecture Analysis
6. Code Quality
7. Testing
8. Git Health
9. Documentation
10. Dependencies
11. Findings
12. AI Engineering Review
13. Recommendations
14. Analysis Metadata

---

# 11. CLI

Example:

```powershell
repolens analyze https://github.com/user/project
```

Potential commands:

```text
repolens analyze
repolens report
repolens findings
repolens version
```

The CLI invokes Application services. It does not implement analysis logic.

---

# 12. Web/API

The web layer provides:

- New Analysis
- Analysis Details
- Findings
- Reports
- Settings

Potential API:

```text
POST /api/v1/analyses
GET  /api/v1/analyses
GET  /api/v1/analyses/{id}
GET  /api/v1/analyses/{id}/findings
GET  /api/v1/analyses/{id}/report
```

---

# 13. Persistence

Initial stack:

- SQLite
- SQLAlchemy

Persist data required for:

- analyses
- findings
- repository metadata
- reports
- AI reviews
- status
- timestamps

---

# 14. Security Boundary

GitHub repositories are untrusted input.

Default MVP behavior is static/read-only analysis.

Arbitrary repository code must not be executed automatically.

Test/build/script execution must be explicit and controlled.

---

# 15. Engineering Standards

Implementation should use:

- clean naming
- Type Hints
- focused functions/classes
- explicit dependencies
- specific exceptions
- logging
- tests
- configuration separation
- secure defaults
- maintainable modules

SOLID and related practices should be used where they improve design, not as ceremonial requirements.

---

# 16. Git/GitHub Workflow

Solo development will follow a professional workflow:

```text
Issue
→ Feature Branch
→ Plan
→ Implementation
→ Tests
→ Diff Review
→ Commit
→ Push
→ Pull Request
→ CI
→ Merge
→ Release
```

The user executes Git write commands unless explicitly delegating them.

Conventional Commits are required.

---

# 17. Vibe Coding

AI agents are part of the development workflow.

The process is:

```text
Intent
→ Constraints
→ Plan
→ Implementation
→ Tests
→ Diff Review
→ Human Acceptance
```

The human owns Architecture and acceptance decisions.

---

# 18. Success Criteria

A fresh developer should be able to:

1. Clone the repository.
2. Follow setup instructions.
3. Start the application.
4. Provide a GitHub URL.
5. Run an analysis.
6. Inspect Findings.
7. View an engineering report.
8. Understand the system from the documentation.

---

# 19. Post-MVP

Future extensions may include:

- GitHub API integration
- authenticated/private repositories
- additional repository providers
- more languages
- security scanners
- vulnerability databases
- PR analysis
- repository history intelligence
- RAG
- scheduled analyses
- team collaboration
- cloud deployment
- background workers
- PostgreSQL
- advanced anomaly detection

These are not required for MVP.
