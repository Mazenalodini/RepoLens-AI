"""Unit tests for WorkspaceSourceReader."""

from unittest.mock import patch

import pytest

from repolens.domain.discovery import FileClassification, FileDescriptor, RepositorySnapshot
from repolens.domain.exceptions import PathTraversalError
from repolens.domain.repository import RepositoryInfo, RepositoryWorkspace
from repolens.domain.source_reader import (
    CumulativeLimitExceededError,
    DiscoveredFileAccessError,
    FileModifiedError,
    FileTooLargeError,
)
from repolens.infrastructure.source_reader import (
    MAX_FILE_BYTES,
    WorkspaceSourceReader,
)


@pytest.fixture
def empty_snapshot() -> RepositorySnapshot:
    return RepositorySnapshot(
        repository_info=RepositoryInfo("owner", "repo", "url", "clone_url"),
        files=(),
        directories=(),
        project_metadata=None,
        total_files=0,
        total_directories=0,
        total_size_bytes=0,
        extension_counts=(),
        language_counts=(),
        classification_counts=(),
    )


def test_reader_rejects_undiscovered_file(tmp_path, empty_snapshot):
    workspace = RepositoryWorkspace(tmp_path, RepositoryInfo("o", "r", "u", "c"))
    reader = WorkspaceSourceReader(workspace, empty_snapshot)

    desc = FileDescriptor("secret.py", "secret.py", ".py", 100, "Python", FileClassification.SOURCE)

    with pytest.raises(DiscoveredFileAccessError, match="not in snapshot"):
        reader.read_descriptor(desc)


def test_reader_respects_workspace_traversal_protection(tmp_path):
    desc = FileDescriptor(
        "../out_of_bounds.py", "out_of_bounds.py", ".py", 100, "Python", FileClassification.SOURCE
    )

    snapshot = RepositorySnapshot(
        repository_info=RepositoryInfo("owner", "repo", "url", "clone_url"),
        files=(desc,),
        directories=(),
        project_metadata=None,
        total_files=1,
        total_directories=0,
        total_size_bytes=100,
        extension_counts=(),
        language_counts=(),
        classification_counts=(),
    )
    workspace = RepositoryWorkspace(tmp_path, RepositoryInfo("o", "r", "u", "c"))
    reader = WorkspaceSourceReader(workspace, snapshot)

    with pytest.raises(PathTraversalError):
        reader.read_descriptor(desc)


def test_reader_reads_valid_file(tmp_path):
    desc = FileDescriptor("test.py", "test.py", ".py", 15, "Python", FileClassification.SOURCE)
    snapshot = RepositorySnapshot(
        repository_info=RepositoryInfo("o", "r", "u", "c"),
        files=(desc,),
        directories=(),
        project_metadata=None,
        total_files=1,
        total_directories=0,
        total_size_bytes=15,
        extension_counts=(),
        language_counts=(),
        classification_counts=(),
    )
    workspace = RepositoryWorkspace(tmp_path, RepositoryInfo("o", "r", "u", "c"))
    file_path = tmp_path / "test.py"
    file_path.write_text("print('hello')\n")

    reader = WorkspaceSourceReader(workspace, snapshot)
    content = reader.read_descriptor(desc)
    assert content.strip() == "print('hello')"
    assert reader.bytes_read > 0


def test_reader_rejects_file_exceeding_per_file_limit(tmp_path):
    desc = FileDescriptor(
        "large.py", "large.py", ".py", MAX_FILE_BYTES + 10, "Python", FileClassification.SOURCE
    )
    snapshot = RepositorySnapshot(
        repository_info=RepositoryInfo("o", "r", "u", "c"),
        files=(desc,),
        directories=(),
        project_metadata=None,
        total_files=1,
        total_directories=0,
        total_size_bytes=0,
        extension_counts=(),
        language_counts=(),
        classification_counts=(),
    )
    workspace = RepositoryWorkspace(tmp_path, RepositoryInfo("o", "r", "u", "c"))
    file_path = tmp_path / "large.py"
    # Create file larger than 1MB
    file_path.write_bytes(b"A" * (MAX_FILE_BYTES + 10))

    reader = WorkspaceSourceReader(workspace, snapshot)
    with pytest.raises(FileTooLargeError, match="exceeds 1MB"):
        reader.read_descriptor(desc)

    # Verify no partial bytes were added to the read total
    assert reader.bytes_read == 0


@patch("repolens.infrastructure.source_reader.MAX_TOTAL_BYTES", 500)
@patch("repolens.infrastructure.source_reader.MAX_FILE_BYTES", 400)
def test_reader_rejects_file_exceeding_cumulative_limit(tmp_path):
    desc1 = FileDescriptor("f1.py", "f1.py", ".py", 400, "Python", FileClassification.SOURCE)
    desc2 = FileDescriptor("f2.py", "f2.py", ".py", 200, "Python", FileClassification.SOURCE)
    snapshot = RepositorySnapshot(
        repository_info=RepositoryInfo("o", "r", "u", "c"),
        files=(desc1, desc2),
        directories=(),
        project_metadata=None,
        total_files=2,
        total_directories=0,
        total_size_bytes=0,
        extension_counts=(),
        language_counts=(),
        classification_counts=(),
    )
    workspace = RepositoryWorkspace(tmp_path, RepositoryInfo("o", "r", "u", "c"))
    (tmp_path / "f1.py").write_bytes(b"A" * 400)
    (tmp_path / "f2.py").write_bytes(b"B" * 200)

    reader = WorkspaceSourceReader(workspace, snapshot)

    # First file succeeds (within 400 bytes, total budget 500)
    content = reader.read_descriptor(desc1)
    assert len(content) == 400
    assert reader.bytes_read == 400

    with pytest.raises(
        CumulativeLimitExceededError, match="Cumulative read limit reached before file read"
    ):
        reader.read_descriptor(desc2)

    # Bytes read remains unchanged, the file was not partially parsed
    assert reader.bytes_read == 400


def test_reader_safely_decodes_invalid_utf8(tmp_path):
    desc = FileDescriptor("bad.py", "bad.py", ".py", 10, "Python", FileClassification.SOURCE)
    snapshot = RepositorySnapshot(
        repository_info=RepositoryInfo("o", "r", "u", "c"),
        files=(desc,),
        directories=(),
        project_metadata=None,
        total_files=1,
        total_directories=0,
        total_size_bytes=0,
        extension_counts=(),
        language_counts=(),
        classification_counts=(),
    )
    workspace = RepositoryWorkspace(tmp_path, RepositoryInfo("o", "r", "u", "c"))

    # Write invalid UTF-8 bytes
    (tmp_path / "bad.py").write_bytes(b"hello \xff world")

    reader = WorkspaceSourceReader(workspace, snapshot)
    content = reader.read_descriptor(desc)

    assert "hello \ufffd world" in content
    assert reader.bytes_read == 13


def test_reader_rejects_modified_file_shrinks(tmp_path):
    desc = FileDescriptor("test.py", "test.py", ".py", 15, "Python", FileClassification.SOURCE)
    snapshot = RepositorySnapshot(
        repository_info=RepositoryInfo("o", "r", "u", "c"),
        files=(desc,),
        directories=(),
        project_metadata=None,
        total_files=1,
        total_directories=0,
        total_size_bytes=15,
        extension_counts=(),
        language_counts=(),
        classification_counts=(),
    )
    workspace = RepositoryWorkspace(tmp_path, RepositoryInfo("o", "r", "u", "c"))
    file_path = tmp_path / "test.py"
    # Actually write only 5 bytes, simulating that it shrank since discovery/stat
    file_path.write_bytes(b"12345")

    reader = WorkspaceSourceReader(workspace, snapshot)

    class MockStat:
        st_size = 15

    with (
        patch("pathlib.Path.stat", return_value=MockStat()),
        pytest.raises(FileModifiedError, match="size changed during read"),
    ):
        reader.read_descriptor(desc)

    assert reader.bytes_read == 0
