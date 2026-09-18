"""Tests for GitHub URL validation and parsing."""

import pytest

from repolens.domain.exceptions import ValidationError
from repolens.infrastructure.github_source import parse_github_url


class TestValidGitHubURLs:
    """Tests for valid GitHub URL formats."""

    def test_standard_https_url(self) -> None:
        info = parse_github_url("https://github.com/owner/repo")
        assert info.owner == "owner"
        assert info.name == "repo"
        assert info.url == "https://github.com/owner/repo"
        assert info.clone_url == "https://github.com/owner/repo.git"
        assert info.source_type == "github"

    def test_url_with_git_suffix(self) -> None:
        info = parse_github_url("https://github.com/owner/repo.git")
        assert info.owner == "owner"
        assert info.name == "repo"
        assert info.clone_url == "https://github.com/owner/repo.git"

    def test_url_with_trailing_slash(self) -> None:
        info = parse_github_url("https://github.com/owner/repo/")
        assert info.owner == "owner"
        assert info.name == "repo"

    def test_url_with_tree_path(self) -> None:
        info = parse_github_url("https://github.com/owner/repo/tree/main")
        assert info.owner == "owner"
        assert info.name == "repo"

    def test_url_with_blob_path(self) -> None:
        info = parse_github_url("https://github.com/owner/repo/blob/main/file.py")
        assert info.owner == "owner"
        assert info.name == "repo"

    def test_http_normalized_to_https(self) -> None:
        info = parse_github_url("http://github.com/owner/repo")
        assert info.url == "https://github.com/owner/repo"
        assert info.clone_url == "https://github.com/owner/repo.git"

    def test_url_without_scheme(self) -> None:
        info = parse_github_url("github.com/owner/repo")
        assert info.owner == "owner"
        assert info.name == "repo"
        assert info.url == "https://github.com/owner/repo"

    def test_www_github_url(self) -> None:
        info = parse_github_url("https://www.github.com/owner/repo")
        assert info.owner == "owner"
        assert info.name == "repo"

    def test_url_with_whitespace(self) -> None:
        info = parse_github_url("  https://github.com/owner/repo  ")
        assert info.owner == "owner"
        assert info.name == "repo"

    def test_owner_with_hyphens(self) -> None:
        info = parse_github_url("https://github.com/my-org/my-repo")
        assert info.owner == "my-org"
        assert info.name == "my-repo"

    def test_repo_with_dots_and_underscores(self) -> None:
        info = parse_github_url("https://github.com/owner/my.repo_name")
        assert info.name == "my.repo_name"

    def test_full_name_property(self) -> None:
        info = parse_github_url("https://github.com/owner/repo")
        assert info.full_name == "owner/repo"


class TestNormalizationDeterminism:
    """Tests that normalization is deterministic and consistent."""

    def test_different_formats_produce_same_result(self) -> None:
        urls = [
            "https://github.com/owner/repo",
            "https://github.com/owner/repo.git",
            "https://github.com/owner/repo/",
            "http://github.com/owner/repo",
            "github.com/owner/repo",
            "https://github.com/owner/repo/tree/main",
        ]
        results = [parse_github_url(u) for u in urls]
        assert all(r.owner == "owner" for r in results)
        assert all(r.name == "repo" for r in results)
        assert all(r.url == "https://github.com/owner/repo" for r in results)
        assert all(r.clone_url == "https://github.com/owner/repo.git" for r in results)


class TestInvalidGitHubURLs:
    """Tests for invalid URL rejection."""

    def test_empty_string(self) -> None:
        with pytest.raises(ValidationError, match="required"):
            parse_github_url("")

    def test_whitespace_only(self) -> None:
        with pytest.raises(ValidationError, match="required"):
            parse_github_url("   ")

    def test_non_github_host(self) -> None:
        with pytest.raises(ValidationError, match="Not a GitHub URL"):
            parse_github_url("https://gitlab.com/owner/repo")

    def test_random_string(self) -> None:
        with pytest.raises(ValidationError):
            parse_github_url("not-a-url-at-all")

    def test_github_without_repo(self) -> None:
        with pytest.raises(ValidationError):
            parse_github_url("https://github.com/owner")

    def test_github_root_only(self) -> None:
        with pytest.raises(ValidationError):
            parse_github_url("https://github.com/")

    def test_github_no_path(self) -> None:
        with pytest.raises(ValidationError):
            parse_github_url("https://github.com")

    def test_ftp_scheme(self) -> None:
        with pytest.raises(ValidationError):
            parse_github_url("ftp://github.com/owner/repo")

    def test_ssh_url_rejected(self) -> None:
        with pytest.raises(ValidationError):
            parse_github_url("git@github.com:owner/repo.git")
