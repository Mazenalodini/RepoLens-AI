"""RepoLens AI — GitHub repository source.

Implements repository acquisition from GitHub via git clone.
Includes URL validation, normalization, and controlled workspace creation.
"""

from __future__ import annotations

import logging
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from repolens.domain.exceptions import AcquisitionError, ValidationError, WorkspaceError
from repolens.domain.repository import RepositoryInfo, RepositoryWorkspace
from repolens.infrastructure.git_client import DEFAULT_CLONE_TIMEOUT, GitClient

logger = logging.getLogger(__name__)

# Matches /owner/repo with optional additional path segments.
# Owner and name: alphanumeric, hyphens, underscores, dots.
_GITHUB_PATH_RE = re.compile(
    r"^/(?P<owner>[a-zA-Z0-9][a-zA-Z0-9\-_.]*)"
    r"/(?P<name>[a-zA-Z0-9][a-zA-Z0-9\-_.]*)"
)

_GITHUB_HOSTS = frozenset({"github.com", "www.github.com"})


def parse_github_url(url: str) -> RepositoryInfo:
    """Parse and validate a GitHub repository URL.

    Accepts various GitHub URL formats and normalizes them::

        https://github.com/owner/repo
        https://github.com/owner/repo.git
        https://github.com/owner/repo/tree/main/...
        http://github.com/owner/repo  (normalized to https)
        github.com/owner/repo        (scheme added)

    Args:
        url: GitHub repository URL string.

    Returns:
        RepositoryInfo with normalized URLs.

    Raises:
        ValidationError: If the URL is empty, malformed, or not a
            valid GitHub repository URL.
    """
    if not url or not url.strip():
        raise ValidationError("Repository URL is required")

    url = url.strip()

    # Add scheme if missing
    if not url.startswith(("http://", "https://")):
        if url.startswith(("github.com", "www.github.com")):
            url = f"https://{url}"
        else:
            raise ValidationError(f"Not a GitHub URL: {url}")

    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise ValidationError(f"Malformed URL: {url}") from exc

    if parsed.scheme not in ("http", "https"):
        raise ValidationError(f"Unsupported URL scheme '{parsed.scheme}': {url}")

    hostname = (parsed.hostname or "").lower()
    if hostname not in _GITHUB_HOSTS:
        raise ValidationError(f"Not a GitHub URL (host: {hostname}): {url}")

    if not parsed.path or parsed.path == "/":
        raise ValidationError(f"No repository path in URL: {url}")

    match = _GITHUB_PATH_RE.match(parsed.path)
    if not match:
        raise ValidationError(f"Cannot extract owner/repo from URL: {url}")

    owner = match.group("owner")
    name = match.group("name")

    # Strip .git suffix
    if name.endswith(".git"):
        name = name[:-4]

    if not name:
        raise ValidationError(f"Empty repository name in URL: {url}")

    normalized_url = f"https://github.com/{owner}/{name}"
    clone_url = f"https://github.com/{owner}/{name}.git"

    return RepositoryInfo(
        owner=owner,
        name=name,
        url=normalized_url,
        clone_url=clone_url,
        source_type="github",
    )


class GitHubRepositorySource:
    """Acquires repositories from GitHub via git clone.

    Satisfies the ``RepositorySource`` protocol. Creates a controlled
    temporary workspace for each acquisition.

    Usage::

        source = GitHubRepositorySource()
        with source.acquire("https://github.com/owner/repo") as workspace:
            print(workspace.root)
    """

    def __init__(
        self,
        git_client: GitClient | None = None,
        base_dir: Path | None = None,
        clone_timeout: int = DEFAULT_CLONE_TIMEOUT,
    ) -> None:
        """Initialize GitHub repository source.

        Args:
            git_client: Git client for clone operations. Uses default if None.
            base_dir: Base directory for temp workspaces. Uses system temp if None.
            clone_timeout: Maximum seconds for clone operations.
        """
        self._git = git_client or GitClient()
        self._base_dir = base_dir
        self._clone_timeout = clone_timeout

    def acquire(self, source: str) -> RepositoryWorkspace:
        """Acquire a GitHub repository.

        Args:
            source: GitHub repository URL.

        Returns:
            RepositoryWorkspace containing the cloned repository.
            Caller is responsible for cleanup (use as context manager).

        Raises:
            ValidationError: If the URL is invalid.
            AcquisitionError: If cloning fails.
            WorkspaceError: If workspace directory creation fails.
        """
        info = parse_github_url(source)

        logger.info("Acquiring repository: %s", info.full_name)

        # Create temporary workspace directory
        try:
            temp_dir = Path(
                tempfile.mkdtemp(
                    prefix="repolens_",
                    dir=self._base_dir,
                )
            )
        except OSError as exc:
            raise WorkspaceError(
                f"Failed to create workspace directory: {exc}"
            ) from exc

        repo_dir = temp_dir / info.name

        try:
            self._git.clone(
                url=info.clone_url,
                target=repo_dir,
                timeout=self._clone_timeout,
            )
        except Exception:
            # Clean up temp directory on acquisition failure
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

        # Verify clone produced a directory
        if not repo_dir.is_dir():
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise AcquisitionError(
                f"Git clone completed but repository directory not found: {repo_dir}"
            )

        logger.info("Repository acquired: %s -> %s", info.full_name, repo_dir)

        return RepositoryWorkspace(
            root=repo_dir,
            info=info,
            _temp_dir=temp_dir,
        )
