"""Tests for GitHubRepositorySource with test doubles."""

import shutil
import tempfile
from pathlib import Path

import pytest

from repolens.domain.exceptions import AcquisitionError, ValidationError
from repolens.domain.repository import RepositoryWorkspace
from repolens.infrastructure.git_client import GitClient
from repolens.infrastructure.github_source import GitHubRepositorySource


class FakeGitClient(GitClient):
    """Test double that simulates git clone by creating directories."""

    def __init__(
        self, *, should_fail: bool = False, error: Exception | None = None
    ) -> None:
        self.should_fail = should_fail
        self.error = error
        self.clone_calls: list[dict[str, object]] = []

    def clone(
        self,
        url: str,
        target: Path,
        *,
        depth: int | None = None,
        timeout: int = 300,
    ) -> None:
        self.clone_calls.append({
            "url": url,
            "target": target,
            "depth": depth,
            "timeout": timeout,
        })

        if self.should_fail:
            raise self.error or AcquisitionError("Fake clone failure")

        # Simulate successful clone
        target.mkdir(parents=True, exist_ok=True)
        (target / "README.md").write_text("# Fake cloned repo")


class TestAcquireSuccess:
    """Tests for successful repository acquisition."""

    def test_acquire_returns_workspace(self) -> None:
        source = GitHubRepositorySource(git_client=FakeGitClient())
        with source.acquire("https://github.com/owner/repo") as workspace:
            assert isinstance(workspace, RepositoryWorkspace)
            assert workspace.root.is_dir()

    def test_acquire_workspace_has_correct_info(self) -> None:
        source = GitHubRepositorySource(git_client=FakeGitClient())
        with source.acquire("https://github.com/owner/repo") as workspace:
            assert workspace.info.owner == "owner"
            assert workspace.info.name == "repo"
            assert workspace.info.full_name == "owner/repo"
            assert workspace.info.source_type == "github"

    def test_acquire_passes_clone_url(self) -> None:
        fake = FakeGitClient()
        source = GitHubRepositorySource(git_client=fake)
        with source.acquire("https://github.com/owner/repo"):
            assert len(fake.clone_calls) == 1
            assert fake.clone_calls[0]["url"] == "https://github.com/owner/repo.git"

    def test_acquire_passes_timeout(self) -> None:
        fake = FakeGitClient()
        source = GitHubRepositorySource(git_client=fake, clone_timeout=60)
        with source.acquire("https://github.com/owner/repo"):
            assert fake.clone_calls[0]["timeout"] == 60

    def test_acquire_repo_dir_uses_name(self) -> None:
        source = GitHubRepositorySource(git_client=FakeGitClient())
        with source.acquire("https://github.com/owner/my-project") as workspace:
            assert workspace.root.name == "my-project"

    def test_acquire_cleans_up_on_context_exit(self) -> None:
        source = GitHubRepositorySource(git_client=FakeGitClient())
        with source.acquire("https://github.com/owner/repo") as workspace:
            parent = workspace.root.parent
            assert parent.exists()
        assert not parent.exists()


class TestAcquireWithBaseDir:
    """Tests for workspace directory placement."""

    def test_workspace_created_in_base_dir(self) -> None:
        base = Path(tempfile.mkdtemp(prefix="repolens_base_"))
        try:
            source = GitHubRepositorySource(git_client=FakeGitClient(), base_dir=base)
            with source.acquire("https://github.com/owner/repo") as workspace:
                assert str(workspace.root.parent).startswith(str(base))
        finally:
            shutil.rmtree(base, ignore_errors=True)


class TestAcquireValidation:
    """Tests for input validation during acquisition."""

    def test_invalid_url_raises_validation_error(self) -> None:
        source = GitHubRepositorySource(git_client=FakeGitClient())
        with pytest.raises(ValidationError):
            source.acquire("not-a-url")

    def test_empty_url_raises_validation_error(self) -> None:
        source = GitHubRepositorySource(git_client=FakeGitClient())
        with pytest.raises(ValidationError, match="required"):
            source.acquire("")

    def test_non_github_url_raises_validation_error(self) -> None:
        source = GitHubRepositorySource(git_client=FakeGitClient())
        with pytest.raises(ValidationError, match="Not a GitHub URL"):
            source.acquire("https://gitlab.com/owner/repo")


class TestAcquireFailure:
    """Tests for acquisition failure handling."""

    def test_clone_failure_raises(self) -> None:
        fake = FakeGitClient(should_fail=True, error=AcquisitionError("Clone failed"))
        source = GitHubRepositorySource(git_client=fake)
        with pytest.raises(AcquisitionError, match="Clone failed"):
            source.acquire("https://github.com/owner/repo")

    def test_clone_failure_cleans_up_temp_dir(self) -> None:
        base = Path(tempfile.mkdtemp(prefix="repolens_base_"))
        try:
            fake = FakeGitClient(
                should_fail=True, error=AcquisitionError("fail")
            )
            source = GitHubRepositorySource(git_client=fake, base_dir=base)

            dirs_before = set(base.iterdir())

            with pytest.raises(AcquisitionError):
                source.acquire("https://github.com/owner/repo")

            dirs_after = set(base.iterdir())
            assert dirs_after == dirs_before  # Temp dir was cleaned up
        finally:
            shutil.rmtree(base, ignore_errors=True)


class TestProtocolConformance:
    """Tests that GitHubRepositorySource satisfies RepositorySource."""

    def test_has_acquire_method(self) -> None:
        source = GitHubRepositorySource(git_client=FakeGitClient())
        assert callable(getattr(source, "acquire", None))
