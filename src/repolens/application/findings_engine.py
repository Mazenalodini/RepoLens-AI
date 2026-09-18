"""RepoLens AI — Findings Engine.

Orchestrates the evaluation of finding rules against structured evidence
to produce normalized, deterministic findings.
"""

import logging

from repolens.domain.evidence import Evidence
from repolens.domain.finding import Finding, FindingRule, FindingsResult

logger = logging.getLogger(__name__)


class FindingRuleRegistry:
    """Collects finding rules and prevents duplicate registrations."""

    def __init__(self) -> None:
        self._rules: list[FindingRule] = []
        self._ids: set[str] = set()

    def register(self, rule: FindingRule) -> None:
        """Register a finding rule. Raises ValueError on duplicate rule_id."""
        if rule.rule_id in self._ids:
            raise ValueError(
                f"Finding rule with ID '{rule.rule_id}' is already registered."
            )
        self._rules.append(rule)
        self._ids.add(rule.rule_id)

    @property
    def rules(self) -> tuple[FindingRule, ...]:
        """Return registered rules in insertion order."""
        return tuple(self._rules)


class FindingsEngine:
    """Evaluates all registered rules against evidence to produce findings.

    The engine operates only on structured evidence. It does not:
    - read repository files
    - perform discovery
    - call AI
    - invent facts or metrics
    """

    def __init__(self, registry: FindingRuleRegistry) -> None:
        self._registry = registry

    def evaluate(self, evidence: tuple[Evidence, ...]) -> FindingsResult:
        """Evaluate all rules and return deterministic findings."""
        all_findings: list[Finding] = []

        for rule in self._registry.rules:
            try:
                findings = rule.evaluate(evidence)
                all_findings.extend(findings)
            except Exception:
                logger.exception(
                    "Finding rule '%s' failed during evaluation.",
                    rule.rule_id,
                )
                # Rule failure is isolated; other rules continue

        # Sort deterministically by (severity ordinal, category, rule_id, finding_id)
        severity_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
            "info": 4,
        }
        all_findings.sort(
            key=lambda f: (
                severity_order.get(f.severity.value, 99),
                f.category.value,
                f.rule_id,
                f.finding_id,
            )
        )

        return FindingsResult(findings=tuple(all_findings))
