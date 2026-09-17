"""RepoLens AI — AI-Powered GitHub Repository Intelligence & Engineering Health Platform."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("repolens")
except PackageNotFoundError:
    __version__ = "0.1.0-dev"
