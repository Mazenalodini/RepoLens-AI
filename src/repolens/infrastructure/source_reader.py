"""RepoLens AI — Workspace Source Reader Implementation.

Provides bounded, safe file reading for an already-discovered repository.
"""

import os

from repolens.domain.discovery import FileDescriptor, RepositorySnapshot
from repolens.domain.repository import RepositoryWorkspace
from repolens.domain.source_reader import (
    BoundedSourceReader,
    CumulativeLimitExceededError,
    DiscoveredFileAccessError,
    FileModifiedError,
    FileTooLargeError,
)

# Constants for strict resource limits
MAX_FILE_BYTES = 1024 * 1024  # 1 MB
MAX_TOTAL_BYTES = 5 * 1024 * 1024  # 5 MB


class WorkspaceSourceReader(BoundedSourceReader):
    """Enforces byte-level read limits and discovered-path restrictions."""

    def __init__(self, workspace: RepositoryWorkspace, snapshot: RepositorySnapshot) -> None:
        self._workspace = workspace
        # Store an immutable set of allowed paths to restrict arbitrary access
        self._allowed_paths = frozenset(f.path for f in snapshot.files)
        self._bytes_read = 0

    @property
    def bytes_read(self) -> int:
        return self._bytes_read

    def read_descriptor(self, descriptor: FileDescriptor) -> str:
        """Read file safely, enforcing boundaries and strict limits."""
        if descriptor.path not in self._allowed_paths:
            raise DiscoveredFileAccessError(f"Path not in snapshot: {descriptor.path}")

        physical_path = self._workspace.resolve_path(descriptor.path)
        actual_size = physical_path.stat().st_size

        if actual_size > MAX_FILE_BYTES:
            raise FileTooLargeError(f"File {descriptor.path} exceeds 1MB limit.")

        if self._bytes_read + actual_size > MAX_TOTAL_BYTES:
            raise CumulativeLimitExceededError("Cumulative read limit reached before file read.")

        with physical_path.open("rb") as f:
            # Read exactly the validated size. We never request more bytes than the
            # already validated complete file size.
            raw_bytes = f.read(actual_size)

            # Check for race-condition growth or shrink.
            # If the file size is now different from what we validated and read,
            # or if we couldn't read the full expected length (shrank),
            # we have a partial file. We abort to maintain complete-file semantics.
            if len(raw_bytes) != actual_size or os.fstat(f.fileno()).st_size != actual_size:
                raise FileModifiedError(
                    f"File {descriptor.path} size changed during read, aborting."
                )

            # Update counter only for fully accepted, complete files.
            self._bytes_read += actual_size

            # Explicitly assuming UTF-8 and safely decoding with replace.
            return raw_bytes.decode("utf-8", errors="replace")
