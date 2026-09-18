"""RepoLens AI — Code Quality Analyzer.

Produces objective, deterministic engineering evidence from source-code content.
"""

import ast

from repolens.domain.analyzer import Analyzer, AnalyzerResult, AnalyzerStatus
from repolens.domain.discovery import FileClassification, RepositorySnapshot
from repolens.domain.evidence import Evidence, MeasuredMetric, ObservedFact
from repolens.domain.source_reader import (
    BoundedSourceReader,
    CumulativeLimitExceededError,
    FileModifiedError,
    FileTooLargeError,
)


class CodeQualityAnalyzer(Analyzer):
    """Parses fully-read Python files to generate AST-based counts and facts."""

    def __init__(self, source_reader: BoundedSourceReader) -> None:
        self._source_reader = source_reader

    @property
    def analyzer_id(self) -> str:
        return "code_quality"

    def analyze(self, snapshot: RepositorySnapshot) -> AnalyzerResult:
        evidence: list[Evidence] = []

        # 1. Deterministic Selection
        target_files = [
            f
            for f in snapshot.files
            if f.language == "Python" and f.classification == FileClassification.SOURCE
        ]

        # Sort alphabetically by path to guarantee deterministic order
        target_files.sort(key=lambda f: f.path)

        python_source_file_count = 0
        python_source_lines = 0
        function_count = 0
        class_count = 0

        for descriptor in target_files:
            try:
                # Strictly read complete file
                content = self._source_reader.read_descriptor(descriptor)

                # File was fully read successfully
                python_source_file_count += 1
                python_source_lines += len(content.splitlines())

                # Attempt to parse AST
                tree = ast.parse(content, filename=descriptor.path)

                # If parsed successfully, count elements
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        function_count += 1
                    elif isinstance(node, ast.ClassDef):
                        class_count += 1

            except FileTooLargeError:
                # File exceeds 1 MB
                evidence.append(
                    ObservedFact(
                        analyzer_id=self.analyzer_id,
                        description=(
                            f"Python source file exceeds the 1 MB per-file limit: "
                            f"{descriptor.path}"
                        ),
                    )
                )
                continue

            except FileModifiedError:
                # File size changed during read, rejecting it entirely
                evidence.append(
                    ObservedFact(
                        analyzer_id=self.analyzer_id,
                        description=(
                            f"Analysis halted for file due to concurrent modification: "
                            f"{descriptor.path}"
                        ),
                    )
                )
                continue

            except CumulativeLimitExceededError:
                # Total 5 MB limit hit
                evidence.append(
                    ObservedFact(
                        analyzer_id=self.analyzer_id,
                        description="Analysis halted: the 5 MB cumulative read limit was reached",
                    )
                )
                break

            except SyntaxError:
                # SyntaxError does not fail the analyzer status
                # Line count and file count are preserved, but functions/classes are not counted
                evidence.append(
                    ObservedFact(
                        analyzer_id=self.analyzer_id,
                        description=f"Syntax error in {descriptor.path}",
                    )
                )
                continue

        # Add metric evidence
        evidence.append(
            MeasuredMetric(
                analyzer_id=self.analyzer_id,
                name="python_source_file_count",
                value=python_source_file_count,
            )
        )
        evidence.append(
            MeasuredMetric(
                analyzer_id=self.analyzer_id,
                name="python_source_lines",
                value=python_source_lines,
            )
        )
        evidence.append(
            MeasuredMetric(
                analyzer_id=self.analyzer_id,
                name="function_count",
                value=function_count,
            )
        )
        evidence.append(
            MeasuredMetric(
                analyzer_id=self.analyzer_id,
                name="class_count",
                value=class_count,
            )
        )

        return AnalyzerResult(
            status=AnalyzerStatus.SUCCESS,
            evidence=tuple(evidence),
        )
