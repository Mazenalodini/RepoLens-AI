"""RepoLens AI — SQLAlchemy ORM Models.

Maps domain persistence records to SQLite tables.
"""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from repolens.infrastructure.database import Base


class AnalysisModel(Base):
    """SQLAlchemy model for persisted analyses."""

    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    repository_owner: Mapped[str] = mapped_column(String(255), nullable=False)
    repository_name: Mapped[str] = mapped_column(String(255), nullable=False)
    repository_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)
    completed_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Summary metrics
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    total_directories: Mapped[int] = mapped_column(Integer, default=0)
    total_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    total_evidence: Mapped[int] = mapped_column(Integer, default=0)
    total_findings: Mapped[int] = mapped_column(Integer, default=0)

    # Serialized structured data (JSON strings)
    findings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_review_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_json_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    pipeline_summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    language_summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
