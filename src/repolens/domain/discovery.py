"""RepoLens AI — Repository Discovery Domain Models.

Contains immutable data structures and deterministic classification rules
for representing a repository's discovered structure.
"""

from dataclasses import dataclass
from enum import Enum

from repolens.domain.repository import RepositoryInfo


class FileClassification(Enum):
    """Categories of repository files based on deterministic heuristics."""

    SOURCE = "source"
    TEST = "test"
    DOCUMENTATION = "documentation"
    CONFIGURATION = "configuration"
    DATA = "data"
    OTHER = "other"


@dataclass(frozen=True)
class FileDescriptor:
    """Represents a discovered file within the repository."""

    path: str  # POSIX relative path from repository root
    name: str
    extension: str  # Lowercase, e.g., ".py", or empty string
    size_bytes: int
    language: str | None
    classification: FileClassification


@dataclass(frozen=True)
class DirectoryDescriptor:
    """Represents a discovered directory within the repository."""

    path: str  # POSIX relative path from repository root
    name: str


@dataclass(frozen=True)
class ProjectMetadata:
    """Lightweight project metadata extracted from standard configuration files."""

    name: str | None
    version: str | None


@dataclass(frozen=True)
class RepositorySnapshot:
    """Immutable deterministic snapshot of a repository's structure."""

    repository_info: RepositoryInfo
    files: tuple[FileDescriptor, ...]
    directories: tuple[DirectoryDescriptor, ...]
    project_metadata: ProjectMetadata | None

    # Aggregates (using tuples for deterministic ordered key-value pairs)
    total_files: int
    total_directories: int
    total_size_bytes: int
    extension_counts: tuple[tuple[str, int], ...]
    language_counts: tuple[tuple[str, int], ...]
    classification_counts: tuple[tuple[FileClassification, int], ...]


# Default ignore policy (Centralized)
DEFAULT_IGNORE_DIRECTORIES = frozenset(
    {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "dist",
        "build",
        "target",
        "out",
        ".next",
        ".nuxt",
    }
)

# Extension to language mapping
EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".dart": "Dart",
    ".php": "PHP",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".c": "C",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".html": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
    ".sh": "Shell",
    ".ps1": "PowerShell",
    ".md": "Markdown",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
}


def classify_file(path: str, name: str, extension: str) -> FileClassification:
    """Determine the file classification using deterministic path/extension rules."""
    path_lower = path.lower()
    name_lower = name.lower()

    # 1. Tests
    if (
        "test/" in path_lower
        or "tests/" in path_lower
        or "/test_" in path_lower
        or name_lower.startswith("test_")
        or name_lower.endswith("_test" + extension)
        or name_lower.endswith(".test" + extension)
        or name_lower.endswith(".spec" + extension)
    ):
        return FileClassification.TEST

    if (
        extension == ".md"
        or "docs/" in path_lower
        or "doc/" in path_lower
        or name_lower
        in {
            "readme",
            "readme.md",
            "contributing",
            "contributing.md",
            "changelog",
            "changelog.md",
            "license",
            "license.md",
        }
    ):
        return FileClassification.DOCUMENTATION

    # 3. Configuration
    if extension in {".toml", ".yaml", ".yml", ".ini", ".cfg", ".conf"} or name_lower in {
        "pyproject.toml",
        "package.json",
        "requirements.txt",
        "dockerfile",
        "makefile",
        "gemfile",
        "pom.xml",
        "build.gradle",
        "tox.ini",
        ".eslintrc",
        ".prettierrc",
    }:
        return FileClassification.CONFIGURATION

    # 4. Data
    if extension in {".csv", ".tsv", ".sqlite", ".db", ".parquet"}:
        return FileClassification.DATA

    # 5. Source (Programming languages)
    source_extensions = {
        ".py",
        ".js",
        ".ts",
        ".java",
        ".kt",
        ".dart",
        ".php",
        ".cpp",
        ".cc",
        ".cxx",
        ".c",
        ".cs",
        ".go",
        ".rs",
        ".rb",
        ".swift",
        ".html",
        ".css",
        ".sql",
        ".sh",
        ".ps1",
    }
    if extension in source_extensions:
        return FileClassification.SOURCE

    # If it's a JSON file but wasn't classified as config (like package.json)
    # or test, we label it DATA.
    if extension == ".json":
        return FileClassification.DATA

    return FileClassification.OTHER
