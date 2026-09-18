"""RepoLens AI — Domain exceptions.

Exception hierarchy for RepoLens AI. Upper layers catch domain-level
exceptions while infrastructure layers raise specific subtypes.
"""


class RepoLensError(Exception):
    """Base exception for all RepoLens AI errors."""


class ValidationError(RepoLensError):
    """Input validation failed."""


class AcquisitionError(RepoLensError):
    """Repository acquisition failed."""


class AcquisitionTimeoutError(AcquisitionError):
    """Repository acquisition timed out."""


class RepositoryNotFoundError(AcquisitionError):
    """Repository does not exist or is not accessible."""


class WorkspaceError(RepoLensError):
    """Workspace management error."""


class PathTraversalError(WorkspaceError):
    """Attempted path traversal outside workspace boundary."""


class DiscoveryError(RepoLensError):
    """Repository discovery failed."""


class DiscoveryLimitExceededError(DiscoveryError):
    """Discovery exceeded configured resource limits (e.g., max files/depth)."""


class AnalyzerError(RepoLensError):
    """Raised when a specific analyzer fails."""


class PipelineError(RepoLensError):
    """Raised when the analyzer pipeline fails."""


class AIProviderError(RepoLensError):
    """AI provider call failed."""


class ReportError(RepoLensError):
    """Report generation failed."""


class ConcurrencyLimitError(RepoLensError):
    """Maximum concurrent analyses exceeded."""


class RepositorySizeError(RepoLensError):
    """Repository exceeds configured size limit."""
