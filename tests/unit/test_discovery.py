"""Tests for Repository Discovery Service and Domain Models."""

import tempfile
from pathlib import Path

import pytest

from repolens.application.discovery import RepositoryDiscoveryService
from repolens.domain.discovery import (
    FileClassification,
    classify_file,
)
from repolens.domain.exceptions import DiscoveryLimitExceededError, WorkspaceError
from repolens.domain.repository import RepositoryInfo, RepositoryWorkspace


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
    """Create a workspace with files and directories for testing discovery."""
    temp_dir = Path(tempfile.mkdtemp(prefix="repolens_discovery_test_"))
    repo_dir = temp_dir / "testrepo"
    repo_dir.mkdir()

    # Create files for testing
    (repo_dir / "README.md").write_text("Docs")
    (repo_dir / "main.py").write_text("print('hello')")

    src_dir = repo_dir / "src"
    src_dir.mkdir()
    (src_dir / "app.js").write_text("console.log('hi')")
    (src_dir / "data.json").write_text("{}")

    test_dir = repo_dir / "tests"
    test_dir.mkdir()
    (test_dir / "test_app.py").write_text("def test_hi(): pass")

    git_dir = repo_dir / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("core")

    workspace = RepositoryWorkspace(
        root=repo_dir,
        info=sample_info,
        _temp_dir=temp_dir,
    )

    yield workspace

    if not workspace.is_closed:
        workspace.cleanup()


class TestFileClassification:
    """Tests for the file classification logic."""

    def test_classify_test_files(self) -> None:
        assert classify_file("tests/test_main.py", "test_main.py", ".py") == FileClassification.TEST
        assert classify_file("src/main_test.go", "main_test.go", ".go") == FileClassification.TEST
        assert classify_file("test/helper.js", "helper.js", ".js") == FileClassification.TEST

    def test_classify_documentation(self) -> None:
        assert classify_file("README.md", "README.md", ".md") == FileClassification.DOCUMENTATION
        assert (
            classify_file("docs/api.html", "api.html", ".html") == FileClassification.DOCUMENTATION
        )
        assert classify_file("LICENSE", "LICENSE", "") == FileClassification.DOCUMENTATION

    def test_classify_configuration(self) -> None:
        assert (
            classify_file("pyproject.toml", "pyproject.toml", ".toml")
            == FileClassification.CONFIGURATION
        )
        assert (
            classify_file("package.json", "package.json", ".json")
            == FileClassification.CONFIGURATION
        )
        assert classify_file("config.yml", "config.yml", ".yml") == FileClassification.CONFIGURATION

    def test_classify_source(self) -> None:
        assert classify_file("src/main.py", "main.py", ".py") == FileClassification.SOURCE
        assert classify_file("app.ts", "app.ts", ".ts") == FileClassification.SOURCE
        assert classify_file("utils/math.cpp", "math.cpp", ".cpp") == FileClassification.SOURCE

    def test_classify_data(self) -> None:
        assert classify_file("data/users.csv", "users.csv", ".csv") == FileClassification.DATA
        assert (
            classify_file("dump.sql", "dump.sql", ".sql") == FileClassification.SOURCE
        )  # SQL is source by mapping
        assert classify_file("records.json", "records.json", ".json") == FileClassification.DATA

    def test_classify_other(self) -> None:
        assert classify_file("image.png", "image.png", ".png") == FileClassification.OTHER
        assert classify_file("binary.bin", "binary.bin", ".bin") == FileClassification.OTHER


class TestRepositoryDiscoveryService:
    """Tests for RepositoryDiscoveryService traversing a workspace."""

    def test_discover_basic_repository(self, temp_workspace: RepositoryWorkspace) -> None:
        service = RepositoryDiscoveryService()
        snapshot = service.discover(temp_workspace)

        assert snapshot.total_files == 5
        assert snapshot.total_directories == 2

        # Check files are present and correctly classified
        paths = {f.path for f in snapshot.files}
        assert "README.md" in paths
        assert "main.py" in paths
        assert "src/app.js" in paths
        assert "src/data.json" in paths
        assert "tests/test_app.py" in paths

        # .git should be ignored
        assert ".git/config" not in paths
        dir_paths = {d.path for d in snapshot.directories}
        assert ".git" not in dir_paths

        # Check determinism (files ordered by path)
        assert snapshot.files[0].path == "README.md"
        assert snapshot.files[1].path == "main.py"

        # Check aggregates
        assert dict(snapshot.extension_counts) == {".py": 2, ".md": 1, ".js": 1, ".json": 1}
        assert dict(snapshot.language_counts) == {
            "Python": 2,
            "Markdown": 1,
            "JavaScript": 1,
            "JSON": 1,
        }

        class_counts = dict(snapshot.classification_counts)
        assert class_counts[FileClassification.SOURCE] == 2
        assert class_counts[FileClassification.TEST] == 1
        assert class_counts[FileClassification.DOCUMENTATION] == 1
        assert class_counts[FileClassification.DATA] == 1

    def test_discovery_respects_max_files(self, temp_workspace: RepositoryWorkspace) -> None:
        service = RepositoryDiscoveryService(max_files=3)
        with pytest.raises(DiscoveryLimitExceededError, match="Maximum files exceeded"):
            service.discover(temp_workspace)

    def test_discovery_respects_max_directories(self, temp_workspace: RepositoryWorkspace) -> None:
        service = RepositoryDiscoveryService(max_directories=1)
        with pytest.raises(DiscoveryLimitExceededError, match="Maximum directories exceeded"):
            service.discover(temp_workspace)

    def test_discovery_respects_max_depth(self, temp_workspace: RepositoryWorkspace) -> None:
        service = RepositoryDiscoveryService(max_depth=0)
        with pytest.raises(DiscoveryLimitExceededError, match="Maximum directory depth exceeded"):
            service.discover(temp_workspace)

    def test_discovery_raises_when_workspace_closed(
        self, temp_workspace: RepositoryWorkspace
    ) -> None:
        temp_workspace.cleanup()
        service = RepositoryDiscoveryService()
        with pytest.raises(WorkspaceError, match="closed"):
            service.discover(temp_workspace)

    def test_discovery_skips_external_symlinks(self, temp_workspace: RepositoryWorkspace) -> None:
        """Test that symlinks pointing outside the workspace are ignored."""
        from unittest.mock import MagicMock, patch

        # We mock Path.iterdir to return a fake symlink entry that resolves outside
        service = RepositoryDiscoveryService()

        mock_entry = MagicMock()
        mock_entry.is_symlink.return_value = True

        # Resolves to a path outside the workspace root
        outside_path = Path("/tmp/outside/secret")
        mock_entry.resolve.return_value = outside_path

        with patch("pathlib.Path.iterdir", return_value=[mock_entry]):
            # This should skip the entry and not raise an error or include it
            snapshot = service.discover(temp_workspace)

            paths = {f.path for f in snapshot.files}
            assert len(paths) == 0  # Our mocked dir has only the malicious link

    def test_metadata_extraction_pyproject(self, temp_workspace: RepositoryWorkspace) -> None:
        (temp_workspace.root / "pyproject.toml").write_text(
            '[project]\nname = "test-proj"\nversion = "1.0.0"'
        )
        service = RepositoryDiscoveryService()
        snapshot = service.discover(temp_workspace)

        assert snapshot.project_metadata is not None
        assert snapshot.project_metadata.name == "test-proj"
        assert snapshot.project_metadata.version == "1.0.0"

    def test_metadata_extraction_package_json(self, temp_workspace: RepositoryWorkspace) -> None:
        (temp_workspace.root / "package.json").write_text('{"name": "test-js", "version": "2.0.0"}')
        service = RepositoryDiscoveryService()
        snapshot = service.discover(temp_workspace)

        assert snapshot.project_metadata is not None
        assert snapshot.project_metadata.name == "test-js"
        assert snapshot.project_metadata.version == "2.0.0"

    def test_metadata_malformed_toml_ignored(self, temp_workspace: RepositoryWorkspace) -> None:
        (temp_workspace.root / "pyproject.toml").write_text('[project\nname = "broken')
        service = RepositoryDiscoveryService()
        snapshot = service.discover(temp_workspace)

        assert snapshot.project_metadata is None  # Should gracefully handle TOMLDecodeError

    def test_metadata_malformed_json_ignored(self, temp_workspace: RepositoryWorkspace) -> None:
        (temp_workspace.root / "package.json").write_text('{"name": "broken')
        service = RepositoryDiscoveryService()
        snapshot = service.discover(temp_workspace)

        assert snapshot.project_metadata is None  # Should gracefully handle JSONDecodeError

    def test_metadata_unreadable_ignored(self, temp_workspace: RepositoryWorkspace) -> None:
        import contextlib
        import stat

        file_path = temp_workspace.root / "package.json"
        file_path.write_text('{"name": "test"}')

        # Make the file unreadable to trigger OSError
        with contextlib.suppress(OSError):
            file_path.chmod(stat.S_IWRITE)

        from unittest.mock import patch

        service = RepositoryDiscoveryService()
        with patch("pathlib.Path.read_text", side_effect=OSError("Permission denied")):
            snapshot = service.discover(temp_workspace)

        assert snapshot.project_metadata is None  # Should gracefully handle OSError

    def test_metadata_unexpected_exception_raised(
        self, temp_workspace: RepositoryWorkspace
    ) -> None:
        (temp_workspace.root / "package.json").write_text('{"name": "test"}')
        service = RepositoryDiscoveryService()

        from unittest.mock import patch

        with (
            patch("pathlib.Path.read_text", side_effect=RuntimeError("Unexpected error")),
            pytest.raises(RuntimeError, match="Unexpected error"),
        ):
            service.discover(temp_workspace)
