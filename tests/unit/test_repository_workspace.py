"""Tests for RepositoryWorkspace lifecycle and path safety."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from repolens.domain.exceptions import PathTraversalError, WorkspaceError
from repolens.domain.repository import (
    _MAX_CLEANUP_RETRIES,
    RepositoryInfo,
    RepositoryWorkspace,
)


@pytest.fixture()
def sample_info() -> RepositoryInfo:
    """Standard RepositoryInfo for testing."""
    return RepositoryInfo(
        owner="testowner",
        name="testrepo",
        url="https://github.com/testowner/testrepo",
        clone_url="https://github.com/testowner/testrepo.git",
    )


@pytest.fixture()
def temp_workspace(sample_info: RepositoryInfo):
    """Create a real temp directory workspace for testing."""
    temp_dir = Path(tempfile.mkdtemp(prefix="repolens_test_"))
    repo_dir = temp_dir / "testrepo"
    repo_dir.mkdir()
    (repo_dir / "README.md").write_text("# Test")

    workspace = RepositoryWorkspace(
        root=repo_dir,
        info=sample_info,
        _temp_dir=temp_dir,
    )

    yield workspace

    # Safety net cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestWorkspaceProperties:
    """Tests for workspace property access."""

    def test_root_returns_directory(self, temp_workspace: RepositoryWorkspace) -> None:
        assert temp_workspace.root.is_dir()

    def test_info_returns_repository_info(
        self, temp_workspace: RepositoryWorkspace, sample_info: RepositoryInfo
    ) -> None:
        assert temp_workspace.info == sample_info

    def test_is_closed_initially_false(
        self, temp_workspace: RepositoryWorkspace
    ) -> None:
        assert not temp_workspace.is_closed


class TestPathResolution:
    """Tests for safe path resolution within workspace."""

    def test_resolve_existing_file(
        self, temp_workspace: RepositoryWorkspace
    ) -> None:
        resolved = temp_workspace.resolve_path("README.md")
        assert resolved.name == "README.md"
        assert resolved.is_file()

    def test_resolve_subdirectory(
        self, temp_workspace: RepositoryWorkspace
    ) -> None:
        subdir = temp_workspace.root / "src"
        subdir.mkdir()
        resolved = temp_workspace.resolve_path("src")
        assert resolved.is_dir()

    def test_traversal_with_dotdot_blocked(
        self, temp_workspace: RepositoryWorkspace
    ) -> None:
        with pytest.raises(PathTraversalError, match="traversal"):
            temp_workspace.resolve_path("../../etc/passwd")

    def test_traversal_parent_blocked(
        self, temp_workspace: RepositoryWorkspace
    ) -> None:
        with pytest.raises(PathTraversalError):
            temp_workspace.resolve_path("../outside")

    def test_resolve_after_close_raises(
        self, temp_workspace: RepositoryWorkspace
    ) -> None:
        temp_workspace.cleanup()
        with pytest.raises(WorkspaceError, match="closed"):
            temp_workspace.resolve_path("README.md")


class TestWorkspaceCleanup:
    """Tests for workspace cleanup behavior."""

    def test_cleanup_removes_directory(self, sample_info: RepositoryInfo) -> None:
        temp_dir = Path(tempfile.mkdtemp(prefix="repolens_test_"))
        repo_dir = temp_dir / "testrepo"
        repo_dir.mkdir()

        workspace = RepositoryWorkspace(
            root=repo_dir, info=sample_info, _temp_dir=temp_dir
        )
        workspace.cleanup()

        assert not temp_dir.exists()
        assert workspace.is_closed

    def test_cleanup_is_idempotent(
        self, temp_workspace: RepositoryWorkspace
    ) -> None:
        temp_workspace.cleanup()
        temp_workspace.cleanup()  # Should not raise
        assert temp_workspace.is_closed

    def test_root_after_close_raises(
        self, temp_workspace: RepositoryWorkspace
    ) -> None:
        temp_workspace.cleanup()
        with pytest.raises(WorkspaceError, match="closed"):
            _ = temp_workspace.root

    def test_context_manager_cleans_up(self, sample_info: RepositoryInfo) -> None:
        temp_dir = Path(tempfile.mkdtemp(prefix="repolens_test_"))
        repo_dir = temp_dir / "testrepo"
        repo_dir.mkdir()

        with RepositoryWorkspace(
            root=repo_dir, info=sample_info, _temp_dir=temp_dir
        ) as ws:
            assert ws.root.is_dir()

        assert not temp_dir.exists()

    def test_workspace_without_temp_dir_preserves_directory(
        self, sample_info: RepositoryInfo
    ) -> None:
        """Workspace without _temp_dir does not delete files on cleanup."""
        temp_dir = Path(tempfile.mkdtemp(prefix="repolens_test_"))
        repo_dir = temp_dir / "testrepo"
        repo_dir.mkdir()

        try:
            workspace = RepositoryWorkspace(root=repo_dir, info=sample_info)
            workspace.cleanup()
            assert temp_dir.exists()  # Not deleted
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestWorkspaceRepr:
    """Tests for workspace string representation."""

    def test_repr_open(self, temp_workspace: RepositoryWorkspace) -> None:
        assert "testowner/testrepo" in repr(temp_workspace)
        assert "open" in repr(temp_workspace)

    def test_repr_closed(self, temp_workspace: RepositoryWorkspace) -> None:
        temp_workspace.cleanup()
        assert "closed" in repr(temp_workspace)


class TestWorkspaceCleanupRetry:
    """Tests for cleanup retry strategy and Windows compatibility."""

    _real_rmtree = staticmethod(shutil.rmtree)

    @patch("repolens.domain.repository.time.sleep")
    @patch("repolens.domain.repository.shutil.rmtree")
    def test_transient_failure_then_success(
        self,
        mock_rmtree,
        mock_sleep,
        sample_info: RepositoryInfo,
    ) -> None:
        """Cleanup retries on transient OSError and succeeds."""
        temp_dir = Path(tempfile.mkdtemp(prefix="repolens_test_"))
        repo_dir = temp_dir / "testrepo"
        repo_dir.mkdir()

        try:
            workspace = RepositoryWorkspace(
                root=repo_dir, info=sample_info, _temp_dir=temp_dir
            )

            # Fail once, then succeed
            mock_rmtree.side_effect = [PermissionError("locked"), None]

            workspace.cleanup()

            assert workspace.is_closed
            assert mock_rmtree.call_count == 2
            mock_sleep.assert_called_once()  # One delay between retries
        finally:
            self._real_rmtree(temp_dir, ignore_errors=True)

    @patch("repolens.domain.repository.time.sleep")
    @patch("repolens.domain.repository.shutil.rmtree")
    def test_persistent_failure_exhausts_retries(
        self,
        mock_rmtree,
        mock_sleep,
        sample_info: RepositoryInfo,
    ) -> None:
        """All retries exhausted on persistent failure."""
        temp_dir = Path(tempfile.mkdtemp(prefix="repolens_test_"))
        repo_dir = temp_dir / "testrepo"
        repo_dir.mkdir()

        try:
            workspace = RepositoryWorkspace(
                root=repo_dir, info=sample_info, _temp_dir=temp_dir
            )

            mock_rmtree.side_effect = PermissionError("permanently locked")

            workspace.cleanup()  # Should not raise

            assert workspace.is_closed
            assert mock_rmtree.call_count == _MAX_CLEANUP_RETRIES
            assert mock_sleep.call_count == _MAX_CLEANUP_RETRIES - 1
        finally:
            self._real_rmtree(temp_dir, ignore_errors=True)

    @patch("repolens.domain.repository.time.sleep")
    @patch("repolens.domain.repository.shutil.rmtree")
    def test_failed_cleanup_allows_retry_on_next_call(
        self,
        mock_rmtree,
        mock_sleep,
        sample_info: RepositoryInfo,
    ) -> None:
        """Cleanup can be called again after failure if temp dir still exists."""
        temp_dir = Path(tempfile.mkdtemp(prefix="repolens_test_"))
        repo_dir = temp_dir / "testrepo"
        repo_dir.mkdir()

        try:
            workspace = RepositoryWorkspace(
                root=repo_dir, info=sample_info, _temp_dir=temp_dir
            )

            # First round: all retries fail
            mock_rmtree.side_effect = PermissionError("locked")
            workspace.cleanup()
            first_call_count = mock_rmtree.call_count

            # Second call: succeeds because temp dir still exists
            mock_rmtree.side_effect = None
            workspace.cleanup()

            assert mock_rmtree.call_count > first_call_count
        finally:
            self._real_rmtree(temp_dir, ignore_errors=True)

    def test_cleanup_handles_readonly_files(
        self, sample_info: RepositoryInfo
    ) -> None:
        """Read-only files are cleaned up successfully."""
        import os
        import stat

        temp_dir = Path(tempfile.mkdtemp(prefix="repolens_test_"))
        repo_dir = temp_dir / "testrepo"
        repo_dir.mkdir()

        # Create a read-only file (simulates Git pack files on Windows)
        readonly_file = repo_dir / "readonly.idx"
        readonly_file.write_text("data")
        os.chmod(str(readonly_file), stat.S_IRUSR)

        workspace = RepositoryWorkspace(
            root=repo_dir, info=sample_info, _temp_dir=temp_dir
        )
        workspace.cleanup()

        assert not temp_dir.exists()
        assert workspace.is_closed

    def test_state_accurate_after_failed_cleanup(
        self, sample_info: RepositoryInfo
    ) -> None:
        """Workspace is closed but temp dir exists after failed cleanup."""
        temp_dir = Path(tempfile.mkdtemp(prefix="repolens_test_"))
        repo_dir = temp_dir / "testrepo"
        repo_dir.mkdir()

        try:
            workspace = RepositoryWorkspace(
                root=repo_dir, info=sample_info, _temp_dir=temp_dir
            )

            with patch("repolens.domain.repository.shutil.rmtree", side_effect=PermissionError), \
                 patch("repolens.domain.repository.time.sleep"):
                workspace.cleanup()

            # Workspace is closed (path ops blocked)
            assert workspace.is_closed
            with pytest.raises(WorkspaceError, match="closed"):
                _ = workspace.root

            # But temp dir still exists (cleanup failed)
            assert temp_dir.exists()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_context_manager_on_cleanup_failure(
        self, sample_info: RepositoryInfo
    ) -> None:
        """Context manager exits cleanly even if cleanup fails."""
        temp_dir = Path(tempfile.mkdtemp(prefix="repolens_test_"))
        repo_dir = temp_dir / "testrepo"
        repo_dir.mkdir()

        try:
            with patch("repolens.domain.repository.shutil.rmtree", side_effect=PermissionError), \
                 patch("repolens.domain.repository.time.sleep"):
                with RepositoryWorkspace(
                    root=repo_dir, info=sample_info, _temp_dir=temp_dir
                ) as ws:
                    assert ws.root.is_dir()

                # Should exit without raising
                assert ws.is_closed
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
