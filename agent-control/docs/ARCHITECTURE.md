# RepoLens AI
## Architecture Specification

**Version:** 1.0
**Architecture Style:** Modular Monolith
**Primary Source:** GitHub Repository
**Primary Language:** Python

---

# 1. Architectural Goals

The architecture must provide:

- Separation of Concerns
- Maintainability
- Testability
- Extensibility
- Secure boundaries
- Clear data flow
- Deterministic analysis
- AI-assisted interpretation

Avoid unnecessary distributed-system complexity.

---

# 2. High-Level Flow

```text
GitHub URL
   ↓
Repository Source
   ↓
Controlled Workspace
   ↓
Analysis Orchestrator
   ↓
Analyzer Registry
   ↓
Analyzer Results
   ↓
Findings Engine
   ↓
AI Context Builder
   ↓
AI Provider
   ↓
Validated AI Review
   ↓
Report Engine
   ↓
Persistence
   ↓
HTML / JSON / Markdown
```

---

# 3. Logical Layers

```text
CLI / API
    ↓
Application
    ↓
Domain

Infrastructure
implements technical capabilities required by upper layers
```

Main packages:

```text
domain/
application/
analyzers/
ai/
reports/
infrastructure/
api/
cli/
```

---

# 4. CLI Boundary

Responsibilities:

- command parsing
- basic input validation
- invoking application services
- presenting results

No core analysis logic.

---

# 5. API Boundary

Responsibilities:

- HTTP handling
- request validation
- response serialization
- calling Application services

No direct analyzer implementation.

---

# 6. Application Layer

Orchestrates use cases:

- analyze repository
- retrieve analysis
- retrieve findings
- generate report

Application code should coordinate rather than implement low-level Git/filesystem/provider details.

---

# 7. Domain Layer

Core concepts:

```text
Repository
Analysis
Finding
Severity
AnalysisStatus
AnalyzerResult
Report
AIReview
```

Domain should not depend directly on:

- FastAPI
- SQLAlchemy
- Typer
- external AI vendors
- shell commands

---

# 8. Repository Acquisition

Conceptual abstraction:

```python
class RepositorySource(Protocol):
    def acquire(self, source: str) -> RepositoryWorkspace:
        ...
```

MVP implementation:

```text
GitHubRepositorySource
```

Future possibilities:

```text
LocalRepositorySource
GitLabRepositorySource
ArchiveRepositorySource
```

---

# 9. Workspace

Provide a controlled repository root and lifecycle.

Responsibilities:

- safe path handling
- temporary workspace
- cleanup
- source metadata
- repository identity

Analyzers should use this abstraction.

---

# 10. Analyzer System

Initial analyzers:

```text
RepositoryAnalyzer
CodeQualityAnalyzer
ArchitectureAnalyzer
TestAnalyzer
GitAnalyzer
DocumentationAnalyzer
DependencyAnalyzer
SecurityHygieneAnalyzer
```

Each analyzer has a single primary responsibility.

---

# 11. Analyzer Contract

Conceptual contract:

```python
class Analyzer(Protocol):
    name: str

    def analyze(
        self,
        repository: RepositoryWorkspace,
    ) -> AnalyzerResult:
        ...
```

Analyzer output must be structured and independently testable.

---

# 12. Analyzer Orchestration

Conceptually:

```text
AnalysisOrchestrator
        ↓
AnalyzerRegistry
        ↓
Selected Analyzers
        ↓
Results
```

The orchestrator should not contain analyzer-specific rules.

---

# 13. Findings Engine

Flow:

```text
Analyzer Results
     ↓
Finding Rules
     ↓
Normalized Findings
```

The Findings Engine is responsible for converting evidence into explainable rule-based findings.

---

# 14. Evidence Model

Maintain explicit distinction:

```text
Observed Fact
Measured Metric
Rule-Based Finding
AI Interpretation
Recommendation
```

This is an architectural invariant.

---

# 15. AI Layer

Components:

```text
AIProvider
AIAdvisor
AIContextBuilder
PromptManager
AIResponseValidator
```

Flow:

```text
Structured Evidence
→ Context Builder
→ Prompt Manager
→ Provider
→ Response
→ Validation
→ AIReview
```

---

# 16. AI Context

Do not blindly send the entire repository.

Select:

- important findings
- relevant metrics
- repository metadata
- architecture evidence
- selected code context
- testing evidence
- Git evidence
- documentation signals

Protect sensitive data.

---

# 17. Report Layer

Conceptual interface:

```python
class ReportGenerator(Protocol):
    def generate(self, analysis: AnalysisResult) -> ReportArtifact:
        ...
```

Implementations:

```text
HTMLReportGenerator
JSONReportGenerator
MarkdownReportGenerator
```

Report generation does not re-run analysis.

---

# 18. Persistence

Use repository/data-access abstractions.

Examples:

```text
AnalysisRepository
FindingRepository
ReportRepository
```

SQLAlchemy implementations belong in Infrastructure.

---

# 19. Infrastructure

Contains implementations for:

```text
Filesystem
Git
GitHub Retrieval
Database
Logging
External Tools
AI Providers
```

---

# 20. Security

External repositories are untrusted.

Default:

```text
Acquire
→ Inspect
→ Analyze
```

Not:

```text
Acquire
→ Install
→ Execute
```

No automatic arbitrary repository code execution.

---

# 21. External Commands

Use controlled adapters for:

- Git
- Ruff
- Radon
- optional pytest

Use structured subprocess arguments, not unsafe shell concatenation.

---

# 22. Failure Isolation

A failed analyzer should not erase successful analyzer results.

Example:

```text
RepositoryAnalyzer      SUCCESS
GitAnalyzer             SUCCESS
DocumentationAnalyzer   SUCCESS
CodeQualityAnalyzer     WARNING
DependencyAnalyzer      SUCCESS
```

Failures must be represented explicitly.

---

# 23. Dependency Direction

The preferred dependency relationship is:

```text
CLI / API
   ↓
Application
   ↓
Domain

Infrastructure
   ↓
implements technical contracts
```

The Domain layer remains infrastructure-agnostic.

---

# 24. Testing Boundaries

Unit-test:

- acquisition
- analyzers
- finding rules
- orchestration
- AI context building
- AI validation
- report generation
- API handlers
- CLI commands

Integration-test major cross-module flows.

---

# 25. Architectural Constraints

Do not introduce:

- microservices
- Kubernetes
- message queues
- distributed tracing
- complex event buses

unless a real requirement appears after MVP.

The MVP is intentionally a modular monolith.

---

# 26. Extension Points

Keep these areas replaceable:

- repository sources
- analyzers
- AI providers
- report formats
- persistence implementation
- API versioning

---

# 27. Architectural Change Rule

A significant architectural change must be:

1. explained
2. justified
3. documented in `docs/DECISIONS.md`
4. reflected in this document when appropriate
5. approved by the human developer before implementation

---

# 28. No Fake Intelligence

The system must never convert unsupported AI output into objective repository facts.

Evidence remains the source of measured truth.

---

# 29. MVP Architecture

```text
GitHub URL
→ GitHub Source
→ Workspace
→ Orchestrator
→ Analyzers
→ Findings
→ AI Review
→ Report
```

This is the minimum architecture that must work end-to-end.
