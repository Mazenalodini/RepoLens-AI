"""Unit tests for Analyzer domain models and Evidence."""

from repolens.domain.analyzer import (
    AnalyzerResult,
    AnalyzerStatus,
    PipelineResult,
)
from repolens.domain.evidence import MeasuredMetric, ObservedFact


def test_evidence_sort_key_determinism() -> None:
    fact1 = ObservedFact(analyzer_id="analyzer_z", description="A fact")
    fact2 = ObservedFact(analyzer_id="analyzer_a", description="A fact", location="file.py")
    fact3 = ObservedFact(analyzer_id="analyzer_a", description="Z fact")

    metric1 = MeasuredMetric(analyzer_id="analyzer_b", name="complexity", value=10)
    metric2 = MeasuredMetric(analyzer_id="analyzer_a", name="complexity", value=20)
    metric3 = MeasuredMetric(analyzer_id="analyzer_a", name="lines", value=100, location="file.py")

    evidence_list = [metric3, fact3, fact1, metric2, metric1, fact2]

    sorted_evidence = sorted(evidence_list, key=lambda e: e.sort_key)

    # Sort order:
    # 1. analyzer_id
    # 2. Evidence type (MeasuredMetric < ObservedFact)
    # 3. Type-specific fields

    assert sorted_evidence == [
        metric2,  # analyzer_a, MeasuredMetric, complexity, 20
        metric3,  # analyzer_a, MeasuredMetric, lines, 100, file.py
        fact2,  # analyzer_a, ObservedFact, A fact, file.py
        fact3,  # analyzer_a, ObservedFact, Z fact
        metric1,  # analyzer_b, MeasuredMetric, complexity, 10
        fact1,  # analyzer_z, ObservedFact, A fact (no location)
    ]


def test_analyzer_result_enforces_deterministic_evidence_ordering() -> None:
    metric = MeasuredMetric(analyzer_id="analyzer_a", name="A", value=1)
    fact = ObservedFact(analyzer_id="analyzer_a", description="B")

    # Provide them in reverse order
    result = AnalyzerResult(status=AnalyzerStatus.SUCCESS, evidence=(fact, metric))

    # Should be sorted upon initialization
    assert result.evidence == (metric, fact)


def test_pipeline_result_aggregates_total_evidence() -> None:
    res1 = AnalyzerResult(
        status=AnalyzerStatus.SUCCESS, evidence=(MeasuredMetric("analyzer_1", "A", 1),)
    )
    res2 = AnalyzerResult(
        status=AnalyzerStatus.SUCCESS,
        evidence=(ObservedFact("analyzer_2", "B"), ObservedFact("analyzer_2", "C")),
    )

    pipeline_result = PipelineResult(
        results=(
            ("analyzer_1", res1),
            ("analyzer_2", res2),
        ),
        is_successful=True,
    )

    assert pipeline_result.total_evidence == 3
    assert len(pipeline_result.evidence) == 3
    assert pipeline_result.evidence == res1.evidence + res2.evidence

    assert pipeline_result.get_result("analyzer_2") is res2
    assert pipeline_result.get_result("missing") is None
