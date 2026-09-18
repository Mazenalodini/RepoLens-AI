"""RepoLens AI — Repository domain models.

Core domain concepts for repository acquisition and workspace management.
These types are used across layers — analyzers receive a RepositoryWorkspace
without knowing how the repository was acquired.
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from repolens.domain.exceptions import PathTraversalError, WorkspaceError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RepositoryInfo:
    """Metadata about an acquired repository.

    Attributes:
        owner: Repository owner (e.g. GitHub username or organization).
        name: Repository name.
        url: Normalized repository URL.
        clone_url: URL suitable for git clone.
        source_type: Source provider identifier (e.g. "github").
    """

    owner: str
    name: str
    url: str
    clone_url: str
    source_type: str = "github"

    @property
    def full_name(self) -> str:
        """Return 'owner/name'."""
        return f"{self.owner}/{self.name}"


class RepositoryWorkspace:
    """Controlled workspace containing an acquired repository.

    Provides safe path resolution and lifecycle management (cleanup).
    Supports context manager protocol for automatic cleanup.

    Usage::

        with source.acquire("https://github.com/owner/repo") as workspace:
            root = workspace.root
            readme = workspace.resolve_path("README.md")
    """

    def __init__(
        self,
        root: Path,
        info: RepositoryInfo,
        *,
        _temp_dir: Path | None = None,
    ) -> None:
        """Initialize workspace.

        Args:
            root: Repository root directory.
            info: Repository metadata.
            _temp_dir: Temporary directory to clean up. If None, no
                filesystem cleanup is performed (useful for local repos).
        """
        self._root = root.resolve()
        self._info = info
        self._temp_dir = _temp_dir
        self._closed = False

    @property
    def root(self) -> Path:
        """Repository root directory.

        Raises:
            WorkspaceError: If workspace has been closed.
        """
        if self._closed:
            raise WorkspaceError("Workspace has been closed")
        return self._root

    @property
    def info(self) -> RepositoryInfo:
        """Repository metadata."""
        return self._info

    @property
    def is_closed(self) -> bool:
        """Whether the workspace has been closed."""
        return self._closed

    def resolve_path(self, relative: str | Path) -> Path:
        """Safely resolve a path within the workspace.

        Args:
            relative: Path relative to the workspace root.

        Returns:
            Resolved absolute path guaranteed to be within workspace.

        Raises:
            WorkspaceError: If workspace is closed.
            PathTraversalError: If path escapes workspace boundary.
        """
        if self._closed:
            raise WorkspaceError("Workspace has been closed")

        resolved = (self._root / relative).resolve()

        if not resolved.is_relative_to(self._root):
            raise PathTraversalError(
                f"Path traversal detected: '{relative}' resolves outside workspace"
            )

        return resolved

    def cleanup(self) -> None:
        """Remove the workspace directory.

        Safe to call multiple times. Logs warnings on cleanup failures
        but does not raise exceptions.
        """
        if self._closed:
            return

        self._closed = True

        if self._temp_dir and self._temp_dir.exists():
            try:
                shutil.rmtree(self._temp_dir)
                logger.debug("Cleaned up workspace: %s", self._temp_dir)
            except OSError:
                logger.warning(
                    "Failed to clean up workspace: %s",
                    self._temp_dir,
                    exc_info=True,
                )

    def __enter__(self) -> RepositoryWorkspace:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        self.cleanup()

    def __repr__(self) -> str:
        status = "closed" if self._closed else "open"
        return f"RepositoryWorkspace({self._info.full_name}, {status})"


class RepositorySource(Protocol):
    """Protocol for acquiring repositories from various sources.

    Implementations must return a RepositoryWorkspace that the caller
    is responsible for cleaning up (preferably via context manager).
    """

    def acquire(self, source: str) -> RepositoryWorkspace:
        """Acquire a repository from the given source identifier.

        Args:
            source: Source identifier (e.g. GitHub URL).

        Returns:
            RepositoryWorkspace with the acquired repository.

        Raises:
            ValidationError: If the source identifier is invalid.
            AcquisitionError: If acquisition fails.
        """
        ...
