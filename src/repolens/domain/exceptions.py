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
