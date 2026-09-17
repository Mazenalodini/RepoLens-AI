# RepoLens AI

**AI-Powered GitHub Repository Intelligence & Engineering Health Platform**

> Understand. Analyze. Improve.

---

## What is RepoLens AI?

RepoLens AI is a platform that analyzes GitHub repositories and generates professional engineering health reports.

Given a GitHub repository URL, RepoLens will:

1. Acquire the repository into a controlled workspace
2. Discover repository structure, languages, and metadata
3. Run deterministic analyzers (code quality, testing, git health, documentation, dependencies, security hygiene)
4. Normalize results into structured Findings with severity and evidence
5. Use AI to interpret findings, correlate patterns, and generate recommendations
6. Produce a professional engineering report

### Core Principle

> **Evidence First, AI-Assisted.**

Deterministic analyzers produce objective, measurable evidence. AI interprets and explains — but never invents metrics, test results, or facts not present in the evidence.

---

## Project Status

🔴 **Pre-Alpha — Foundation**

The project is in its initial foundation phase. The package structure and development tooling are being established. No analysis features are implemented yet.

---

## Architecture

RepoLens AI is designed as a **Modular Monolith** with clear separation of concerns:

```text
CLI / API
    ↓
Application (orchestration)
    ↓
Domain (core concepts, no framework dependencies)

Infrastructure (implements technical contracts)
```

For detailed architecture documentation, see [`agent-control/docs/ARCHITECTURE.md`](agent-control/docs/ARCHITECTURE.md).

---

## Development Setup

### Prerequisites

- Python 3.12 or later
- Git

### Installation

```powershell
# Clone the repository
git clone https://github.com/<username>/RepoLens-AI.git
cd RepoLens-AI

# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install in development mode
pip install -e ".[dev]"
```

### Verify Installation

```powershell
python -c "import repolens; print(repolens.__version__)"
```

---

## Testing

```powershell
pytest tests/ -v
```

---

## Linting

```powershell
ruff check src/ tests/
```

---

## Project Structure

```text
RepoLens-AI/
├── AGENTS.md                  # Agent Operating System
├── README.md                  # This file
├── pyproject.toml             # Project configuration
├── .gitignore
├── .env.example               # Environment variable template
├── agent-control/             # Agent Control Kit (docs, instructions, prompts)
├── src/
│   └── repolens/              # Main application package
│       ├── domain/            # Core domain concepts
│       ├── application/       # Use-case orchestration
│       ├── analyzers/         # Analysis modules
│       ├── ai/                # AI interpretation layer
│       ├── reports/           # Report generation
│       ├── infrastructure/    # Technical implementations
│       ├── api/               # HTTP API
│       └── cli/               # Command-line interface
└── tests/
    ├── unit/
    └── integration/
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [`AGENTS.md`](AGENTS.md) | Agent Operating System — rules for AI-assisted development |
| [`agent-control/docs/PROJECT_SPEC.md`](agent-control/docs/PROJECT_SPEC.md) | Product & Engineering Specification |
| [`agent-control/docs/ARCHITECTURE.md`](agent-control/docs/ARCHITECTURE.md) | Architecture Specification |
| [`agent-control/docs/DECISIONS.md`](agent-control/docs/DECISIONS.md) | Architecture Decision Records |
| [`agent-control/docs/ROADMAP.md`](agent-control/docs/ROADMAP.md) | Delivery Roadmap |
| [`agent-control/docs/DEVELOPMENT_WORKFLOW.md`](agent-control/docs/DEVELOPMENT_WORKFLOW.md) | Development Workflow |
