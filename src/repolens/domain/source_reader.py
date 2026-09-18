"""RepoLens AI — Source Reader Domain Models.

Defines the contract for safely reading bounded source code from a
repository workspace without exposing arbitrary filesystem access.
"""

from typing import Protocol

from repolens.domain.discovery import FileDescriptor


class FileTooLargeError(Exception):
    """Raised when a single file exceeds the per-file size limit."""

    pass


class CumulativeLimitExceededError(Exception):
    """Raised when reading a file would exceed the cumulative read budget."""

    pass


class DiscoveredFileAccessError(Exception):
    """Raised when attempting to read a file not in the discovered set."""

    pass


class FileModifiedError(Exception):
    """Raised when a file's size changes during read, preventing complete read semantics."""

    pass


class BoundedSourceReader(Protocol):
    """Protocol for a bounded, safe repository source reader."""

    def read_descriptor(self, descriptor: FileDescriptor) -> str:
        """Read the complete content of a discovered file safely.

        Raises:
            FileTooLargeError: If the file exceeds the per-file limit.
            CumulativeLimitExceededError: If the file exceeds the remaining budget.
            DiscoveredFileAccessError: If the path is not in the allowed set.
            FileModifiedError: If the file changes size during read.
        """
        ...
