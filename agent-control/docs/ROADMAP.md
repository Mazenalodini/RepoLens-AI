# RepoLens AI — Delivery Roadmap

## Phase 0 — Foundation

الهدف: تأسيس المشروع وقواعد الـAgent.

Deliverables:

- repository structure
- pyproject.toml
- AGENTS.md
- documentation baseline
- configuration baseline
- basic CI skeleton
- test skeleton

Acceptance:

- project imports correctly
- tests can run
- linting can run
- documentation explains setup

---

## Phase 1 — Repository Acquisition

Build:

- GitHub URL validation
- RepositorySource abstraction
- GitHub source
- controlled workspace
- cleanup
- acquisition errors

Acceptance:

```text
GitHub URL
→ controlled local workspace
```

---

## Phase 2 — Repository Discovery

Build:

- file discovery
- language detection
- project metadata
- structure extraction
- file classification

Acceptance:

The system can describe a repository without executing it.

---

## Phase 3 — Analyzer Pipeline

Build:

- analyzer protocol
- registry
- orchestrator
- repository analyzer
- Git analyzer
- documentation analyzer
- dependency analyzer

Acceptance:

Multiple analyzers can run independently and return structured results.

---

## Phase 4 — Code Quality

Build:

- deterministic code-quality rules
- Ruff integration where appropriate
- Radon integration where appropriate
- code-quality findings

Acceptance:

Findings are backed by actual evidence.

---

## Phase 5 — Findings Engine

Build:

- normalized Finding model
- rule handling
- severity
- evidence references
- recommendations

Acceptance:

Analyzer observations become standardized findings.

---

## Phase 6 — Testing Intelligence

Build:

- test detection
- supported framework detection
- optional controlled execution path
- real test results

Acceptance:

No fake coverage or fake execution data.

---

## Phase 7 — AI Reasoning

Build:

- AIProvider
- Context Builder
- prompt management
- structured output
- response validation
- AIReview

Acceptance:

AI only receives selected evidence and returns validated structured output.

---

## Phase 8 — Report Engine

Build:

- HTML
- JSON
- Markdown

Acceptance:

A complete analysis can become a professional report.

---

## Phase 9 — Web/API

Build:

- FastAPI
- analysis endpoints
- report endpoints
- findings endpoints
- basic dashboard

Acceptance:

A user can initiate and inspect analysis via the web interface.

---

## Phase 10 — Hardening

Build:

- security checks
- timeouts
- limits
- better failures
- integration tests
- logging

---

## Phase 11 — GitHub Delivery

Build:

- CI
- Issues
- feature branches
- PRs
- release/tag
- documentation polish

---

## Phase 12 — Self Analysis

Run RepoLens AI against its own repository.

Use the output to demonstrate dogfooding.

---

# Priority Rule

The preferred order is:

```text
Working vertical slice
>
Feature completeness
>
Visual polish
>
Advanced integrations
```

Do not sacrifice end-to-end functionality for optional features.
