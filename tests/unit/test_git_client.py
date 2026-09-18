"""Tests for GitClient with mocked subprocess."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from repolens.domain.exceptions import (
    AcquisitionError,
    AcquisitionTimeoutError,
    RepositoryNotFoundError,
)
from repolens.infrastructure.git_client import GitClient


class TestCloneSuccess:
    """Tests for successful clone operations."""

    @patch("repolens.infrastructure.git_client.subprocess.run")
    def test_clone_calls_subprocess(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

        client = GitClient()
        client.clone(url="https://github.com/o/r.git", target=Path("/tmp/t"))

        mock_run.assert_called_once()

    @patch("repolens.infrastructure.git_client.subprocess.run")
    def test_clone_uses_structured_args(self, mock_run: MagicMock) -> None:
        """Subprocess must be called with list args, never shell string."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

        client = GitClient()
        client.clone(url="https://github.com/o/r.git", target=Path("/tmp/t"))

        cmd = mock_run.call_args[0][0]
        assert isinstance(cmd, list)
        assert mock_run.call_args[1].get("shell") is not True

    @patch("repolens.infrastructure.git_client.subprocess.run")
    def test_clone_uses_separator(self, mock_run: MagicMock) -> None:
        """'--' separator must be present to prevent arg injection."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

        client = GitClient()
        client.clone(url="https://github.com/o/r.git", target=Path("/tmp/t"))

        cmd = mock_run.call_args[0][0]
        assert "--" in cmd
        # URL and target must come after '--'
        sep_idx = cmd.index("--")
        assert cmd[sep_idx + 1] == "https://github.com/o/r.git"

    @patch("repolens.infrastructure.git_client.subprocess.run")
    def test_clone_passes_timeout(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

        client = GitClient()
        client.clone(url="https://github.com/o/r.git", target=Path("/tmp/t"), timeout=60)

        assert mock_run.call_args[1]["timeout"] == 60

    @patch("repolens.infrastructure.git_client.subprocess.run")
    def test_clone_without_depth(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

        client = GitClient()
        client.clone(url="https://github.com/o/r.git", target=Path("/tmp/t"))

        cmd = mock_run.call_args[0][0]
        assert "--depth" not in cmd

    @patch("repolens.infrastructure.git_client.subprocess.run")
    def test_clone_with_depth(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

        client = GitClient()
        client.clone(url="https://github.com/o/r.git", target=Path("/tmp/t"), depth=1)

        cmd = mock_run.call_args[0][0]
        depth_idx = cmd.index("--depth")
        assert cmd[depth_idx + 1] == "1"


class TestCloneFailures:
    """Tests for clone failure handling."""

    @patch("repolens.infrastructure.git_client.subprocess.run")
    def test_timeout_raises_acquisition_timeout(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=10)

        client = GitClient()
        with pytest.raises(AcquisitionTimeoutError, match="timed out"):
            client.clone(url="https://github.com/o/r.git", target=Path("/tmp/t"), timeout=10)

    @patch("repolens.infrastructure.git_client.subprocess.run")
    def test_git_not_installed_raises_acquisition_error(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError("git not found")

        client = GitClient()
        with pytest.raises(AcquisitionError, match="not installed"):
            client.clone(url="https://github.com/o/r.git", target=Path("/tmp/t"))

    @patch("repolens.infrastructure.git_client.subprocess.run")
    def test_repo_not_found(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=128,
            stderr="fatal: repository 'https://github.com/x/y.git/' not found",
        )

        client = GitClient()
        with pytest.raises(RepositoryNotFoundError):
            client.clone(url="https://github.com/x/y.git", target=Path("/tmp/t"))

    @patch("repolens.infrastructure.git_client.subprocess.run")
    def test_authentication_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=128,
            stderr="fatal: Authentication failed for 'https://github.com/x/y.git/'",
        )

        client = GitClient()
        with pytest.raises(RepositoryNotFoundError, match="access denied"):
            client.clone(url="https://github.com/x/y.git", target=Path("/tmp/t"))

    @patch("repolens.infrastructure.git_client.subprocess.run")
    def test_generic_failure_preserves_stderr(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="some unknown error occurred",
        )

        client = GitClient()
        with pytest.raises(AcquisitionError, match="exit code 1"):
            client.clone(url="https://github.com/x/y.git", target=Path("/tmp/t"))

    @patch("repolens.infrastructure.git_client.subprocess.run")
    def test_os_error_raises_acquisition_error(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("permission denied")

        client = GitClient()
        with pytest.raises(AcquisitionError, match="Failed to execute"):
            client.clone(url="https://github.com/o/r.git", target=Path("/tmp/t"))
