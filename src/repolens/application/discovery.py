"""RepoLens AI — Repository Discovery Service.

Provides deterministic, limits-bounded filesystem inspection for generating
a repository snapshot, avoiding untrusted code execution.
"""

from collections import defaultdict
from pathlib import Path

from repolens.domain.discovery import (
    DEFAULT_IGNORE_DIRECTORIES,
    EXTENSION_LANGUAGE_MAP,
    DirectoryDescriptor,
    FileClassification,
    FileDescriptor,
    ProjectMetadata,
    RepositorySnapshot,
    classify_file,
)
from repolens.domain.exceptions import DiscoveryLimitExceededError
from repolens.domain.repository import RepositoryWorkspace


class RepositoryDiscoveryService:
    """Service to discover and snapshot repository contents deterministically."""

    def __init__(
        self,
        max_files: int = 10_000,
        max_directories: int = 2_000,
        max_depth: int = 50,
        ignore_directories: frozenset[str] = DEFAULT_IGNORE_DIRECTORIES,
    ):
        """Initialize the discovery service with resource limits and policies."""
        self._max_files = max_files
        self._max_directories = max_directories
        self._max_depth = max_depth
        self._ignore_directories = ignore_directories

    def discover(self, workspace: RepositoryWorkspace) -> RepositorySnapshot:
        """Walks the workspace and builds a deterministic RepositorySnapshot.

        Args:
            workspace: The acquired repository workspace.

        Raises:
            DiscoveryLimitExceededError: If resource limits are exceeded.
            WorkspaceError: If the workspace is closed.
        """
        root = workspace.root  # Will raise WorkspaceError if closed

        files: list[FileDescriptor] = []
        directories: list[DirectoryDescriptor] = []

        total_size_bytes = 0
        extension_counts: dict[str, int] = defaultdict(int)
        language_counts: dict[str, int] = defaultdict(int)
        classification_counts: dict[FileClassification, int] = defaultdict(int)

        # BFS Queue: tuple of (Path, depth)
        queue: list[tuple[Path, int]] = [(root, 0)]

        while queue:
            current_dir, depth = queue.pop(0)

            if depth > self._max_depth:
                raise DiscoveryLimitExceededError(
                    f"Maximum directory depth exceeded ({self._max_depth})"
                )

            try:
                entries = sorted(list(current_dir.iterdir()), key=lambda p: p.name)
            except OSError:
                continue  # Skip unreadable directories

            for entry in entries:
                # Security: prevent symlink escapes
                if entry.is_symlink():
                    try:
                        resolved = entry.resolve()
                        if not resolved.is_relative_to(root):
                            continue  # Escape attempt or external link
                        if not resolved.exists():
                            continue  # Broken link
                    except (OSError, RuntimeError):
                        continue

                # Paths must be relative to workspace root using POSIX separators
                try:
                    rel_path = entry.relative_to(root).as_posix()
                except ValueError:
                    continue  # Should not happen given iterdir, but defensive

                if entry.is_dir():
                    if entry.name in self._ignore_directories:
                        continue

                    if len(directories) >= self._max_directories:
                        raise DiscoveryLimitExceededError(
                            f"Maximum directories exceeded ({self._max_directories})"
                        )

                    directories.append(DirectoryDescriptor(path=rel_path, name=entry.name))
                    queue.append((entry, depth + 1))

                elif entry.is_file():
                    if len(files) >= self._max_files:
                        raise DiscoveryLimitExceededError(
                            f"Maximum files exceeded ({self._max_files})"
                        )

                    try:
                        size = entry.stat().st_size
                    except OSError:
                        size = 0

                    ext = entry.suffix.lower()
                    lang = EXTENSION_LANGUAGE_MAP.get(ext)
                    classification = classify_file(rel_path, entry.name, ext)

                    files.append(
                        FileDescriptor(
                            path=rel_path,
                            name=entry.name,
                            extension=ext,
                            size_bytes=size,
                            language=lang,
                            classification=classification,
                        )
                    )

                    # Accumulate stats
                    total_size_bytes += size
                    extension_counts[ext] += 1
                    if lang:
                        language_counts[lang] += 1
                    classification_counts[classification] += 1

        # Sort files and directories to guarantee determinism
        files.sort(key=lambda f: f.path)
        directories.sort(key=lambda d: d.path)

        # Sort aggregates deterministically
        sorted_ext_counts = tuple(sorted(extension_counts.items(), key=lambda x: (-x[1], x[0])))
        sorted_lang_counts = tuple(sorted(language_counts.items(), key=lambda x: (-x[1], x[0])))
        sorted_class_counts = tuple(
            sorted(classification_counts.items(), key=lambda x: (-x[1], x[0].name))
        )

        project_metadata = self._extract_metadata(root, files)

        return RepositorySnapshot(
            repository_info=workspace.info,
            files=tuple(files),
            directories=tuple(directories),
            project_metadata=project_metadata,
            total_files=len(files),
            total_directories=len(directories),
            total_size_bytes=total_size_bytes,
            extension_counts=sorted_ext_counts,
            language_counts=sorted_lang_counts,
            classification_counts=sorted_class_counts,
        )

    def _extract_metadata(self, root: Path, files: list[FileDescriptor]) -> ProjectMetadata | None:
        """Safely extract lightweight project metadata from standard configuration files.

        Reads only a strictly limited file size and handles parsing defensively.
        """
        import json
        import tomllib

        max_metadata_size = 128 * 1024  # 128 KB

        # Look for pyproject.toml first
        pyproject_file = next((f for f in files if f.path == "pyproject.toml"), None)
        if pyproject_file and pyproject_file.size_bytes <= max_metadata_size:
            try:
                content = (root / pyproject_file.path).read_text(encoding="utf-8")
                data = tomllib.loads(content)
                project = data.get("project", {})

                # Poetry uses tool.poetry
                if not project and "tool" in data and "poetry" in data["tool"]:
                    project = data["tool"]["poetry"]

                name = project.get("name")
                version = project.get("version")
                if name or version:
                    return ProjectMetadata(
                        name=str(name) if name else None,
                        version=str(version) if version else None,
                    )
            except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
                pass  # Safely ignore IO/decoding/parsing errors

        # Fallback to package.json
        package_json = next((f for f in files if f.path == "package.json"), None)
        if package_json and package_json.size_bytes <= max_metadata_size:
            try:
                content = (root / package_json.path).read_text(encoding="utf-8")
                data = json.loads(content)
                name = data.get("name")
                version = data.get("version")
                if name or version:
                    return ProjectMetadata(
                        name=str(name) if name else None,
                        version=str(version) if version else None,
                    )
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                pass  # Safely ignore IO/decoding/parsing errors

        return None
