"""RepoLens AI — Repository Health Analyzer.

Generates objective, deterministic metrics and facts regarding the overall
health and structure of the repository based on the discovery snapshot.
"""

from repolens.domain.analyzer import Analyzer, AnalyzerResult, AnalyzerStatus
from repolens.domain.discovery import FileClassification, RepositorySnapshot
from repolens.domain.evidence import MeasuredMetric, ObservedFact


class RepositoryHealthAnalyzer(Analyzer):
    """Interprets the RepositorySnapshot to produce repository health evidence."""

    @property
    def analyzer_id(self) -> str:
        return "repository_health"

    def analyze(self, snapshot: RepositorySnapshot) -> AnalyzerResult:
        evidence: list[MeasuredMetric | ObservedFact] = []

        # 1. Base Metrics
        evidence.append(
            MeasuredMetric(
                analyzer_id=self.analyzer_id,
                name="total_files",
                value=snapshot.total_files,
            )
        )
        evidence.append(
            MeasuredMetric(
                analyzer_id=self.analyzer_id,
                name="total_directories",
                value=snapshot.total_directories,
            )
        )
        evidence.append(
            MeasuredMetric(
                analyzer_id=self.analyzer_id,
                name="total_size_bytes",
                value=snapshot.total_size_bytes,
            )
        )

        # Helper to get count for a classification
        def get_count(classification: FileClassification) -> int:
            for cls, count in snapshot.classification_counts:
                if cls == classification:
                    return count
            return 0

        total_source_files = get_count(FileClassification.SOURCE)
        total_test_files = get_count(FileClassification.TEST)
        total_documentation_files = get_count(FileClassification.DOCUMENTATION)
        total_configuration_files = get_count(FileClassification.CONFIGURATION)

        # 2. Classification Metrics
        evidence.append(
            MeasuredMetric(
                analyzer_id=self.analyzer_id,
                name="total_source_files",
                value=total_source_files,
            )
        )
        evidence.append(
            MeasuredMetric(
                analyzer_id=self.analyzer_id,
                name="total_test_files",
                value=total_test_files,
            )
        )
        evidence.append(
            MeasuredMetric(
                analyzer_id=self.analyzer_id,
                name="total_documentation_files",
                value=total_documentation_files,
            )
        )
        evidence.append(
            MeasuredMetric(
                analyzer_id=self.analyzer_id,
                name="total_configuration_files",
                value=total_configuration_files,
            )
        )

        # 3. Facts
        # Tests detection
        if total_test_files > 0:
            evidence.append(ObservedFact(self.analyzer_id, "Tests detected"))
        else:
            evidence.append(ObservedFact(self.analyzer_id, "No test files detected"))

        # README detection
        readme_detected = any(f.name.lower() in ("readme.md", "readme") for f in snapshot.files)
        if readme_detected:
            evidence.append(ObservedFact(self.analyzer_id, "README detected"))
        else:
            evidence.append(ObservedFact(self.analyzer_id, "README not detected"))

        # Project Metadata detection
        if snapshot.project_metadata is not None:
            evidence.append(ObservedFact(self.analyzer_id, "Project metadata detected"))
        else:
            evidence.append(ObservedFact(self.analyzer_id, "Project metadata not detected"))

        # Return immutable result, sort happens automatically in AnalyzerResult
        return AnalyzerResult(
            status=AnalyzerStatus.SUCCESS,
            evidence=tuple(evidence),
        )
