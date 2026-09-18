"""RepoLens AI — SQLite Analysis Store.

Implements the AnalysisStore protocol using SQLAlchemy + SQLite.
"""

import logging

from sqlalchemy.orm import Session, sessionmaker

from repolens.domain.persistence import AnalysisRecord
from repolens.infrastructure.db_models import AnalysisModel

logger = logging.getLogger(__name__)

# Fields shared between AnalysisRecord and AnalysisModel
_RECORD_FIELDS = (
    "id",
    "repository_owner",
    "repository_name",
    "repository_url",
    "status",
    "created_at",
    "completed_at",
    "error_message",
    "total_files",
    "total_directories",
    "total_size_bytes",
    "total_evidence",
    "total_findings",
    "findings_json",
    "ai_review_json",
    "report_html",
    "report_json_content",
    "report_markdown",
    "pipeline_summary_json",
    "language_summary_json",
)


def _record_to_model(record: AnalysisRecord) -> AnalysisModel:
    """Convert an AnalysisRecord to an AnalysisModel."""
    return AnalysisModel(**{field: getattr(record, field) for field in _RECORD_FIELDS})


def _model_to_record(model: AnalysisModel) -> AnalysisRecord:
    """Convert an AnalysisModel to an AnalysisRecord."""
    return AnalysisRecord(**{field: getattr(model, field) for field in _RECORD_FIELDS})


class SQLiteAnalysisStore:
    """AnalysisStore implementation backed by SQLite via SQLAlchemy.

    Thread-safe: each operation creates its own session.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save(self, record: AnalysisRecord) -> None:
        """Save a new analysis record."""
        with self._session_factory() as session:
            model = _record_to_model(record)
            session.add(model)
            session.commit()
            logger.debug("Saved analysis record: %s", record.id)

    def update(self, record: AnalysisRecord) -> None:
        """Update an existing analysis record."""
        with self._session_factory() as session:
            model = session.get(AnalysisModel, record.id)
            if model is None:
                logger.warning("Analysis record not found for update: %s", record.id)
                return
            for field in _RECORD_FIELDS:
                if field == "id":
                    continue
                setattr(model, field, getattr(record, field))
            session.commit()
            logger.debug("Updated analysis record: %s", record.id)

    def get(self, analysis_id: str) -> AnalysisRecord | None:
        """Retrieve an analysis record by ID."""
        with self._session_factory() as session:
            model = session.get(AnalysisModel, analysis_id)
            if model is None:
                return None
            return _model_to_record(model)

    def list_recent(self, limit: int = 20) -> list[AnalysisRecord]:
        """Return the most recent analyses, ordered by creation time descending."""
        with self._session_factory() as session:
            models = (
                session.query(AnalysisModel)
                .order_by(AnalysisModel.created_at.desc())
                .limit(limit)
                .all()
            )
            return [_model_to_record(m) for m in models]
