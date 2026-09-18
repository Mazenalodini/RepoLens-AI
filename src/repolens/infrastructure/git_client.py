"""RepoLens AI — Git subprocess client.

Safe wrapper around Git command-line operations using structured
subprocess arguments. No shell string concatenation.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from repolens.domain.exceptions import (
    AcquisitionError,
    AcquisitionTimeoutError,
    RepositoryNotFoundError,
)

logger = logging.getLogger(__name__)

DEFAULT_CLONE_TIMEOUT: int = 300  # 5 minutes


class GitClient:
    """Safe Git subprocess wrapper.

    Uses structured subprocess arguments (never shell=True).
    Handles timeouts and classifies errors into domain exceptions.
    """

    def clone(
        self,
        url: str,
        target: Path,
        *,
        depth: int | None = None,
        timeout: int = DEFAULT_CLONE_TIMEOUT,
    ) -> None:
        """Clone a Git repository.

        Args:
            url: Repository clone URL.
            target: Local directory to clone into.
            depth: If set, perform a shallow clone with this depth.
            timeout: Maximum seconds for the clone operation.

        Raises:
            AcquisitionTimeoutError: If clone exceeds timeout.
            RepositoryNotFoundError: If repository does not exist.
            AcquisitionError: For other Git failures.
        """
        cmd: list[str] = ["git", "clone", "--quiet"]

        if depth is not None:
            cmd.extend(["--depth", str(depth)])

        # '--' separates options from positional arguments (security)
        cmd.extend(["--", url, str(target)])

        logger.info("Cloning repository: %s", url)
        logger.debug("Git command: %s", cmd)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise AcquisitionTimeoutError(
                f"Git clone timed out after {timeout} seconds: {url}"
            ) from exc
        except FileNotFoundError as exc:
            raise AcquisitionError(
                "Git is not installed or not found in PATH. "
                "Install Git: https://git-scm.com/"
            ) from exc
        except OSError as exc:
            raise AcquisitionError(
                f"Failed to execute git command: {exc}"
            ) from exc

        if result.returncode != 0:
            self._classify_and_raise(url, result.returncode, result.stderr.strip())

    def _classify_and_raise(
        self,
        url: str,
        returncode: int,
        stderr: str,
    ) -> None:
        """Classify Git stderr output and raise the appropriate exception."""
        stderr_lower = stderr.lower()

        # Repository not found patterns
        not_found_patterns = (
            "repository not found",
            "does not exist",
            "not found",
            "could not read from remote",
        )
        for pattern in not_found_patterns:
            if pattern in stderr_lower:
                raise RepositoryNotFoundError(
                    f"Repository not found or inaccessible: {url}"
                )

        # Authentication / access denied
        if "authentication" in stderr_lower or "permission denied" in stderr_lower:
            raise RepositoryNotFoundError(
                f"Repository access denied (may be private or not exist): {url}"
            )

        # Generic failure with stderr context
        raise AcquisitionError(
            f"Git clone failed (exit code {returncode}): {stderr}"
        )
