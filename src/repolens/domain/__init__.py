"""RepoLens AI — Domain layer.

Core domain concepts: Repository, Analysis, Finding, Severity, AnalysisStatus,
AnalyzerResult, Report, AIReview.

This layer must remain infrastructure-agnostic. It should not depend on
FastAPI, SQLAlchemy, Typer, external AI vendors, or shell commands.
"""
