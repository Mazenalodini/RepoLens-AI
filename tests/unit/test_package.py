"""Smoke tests for RepoLens AI package."""

import repolens


def test_package_is_importable() -> None:
    """Verify that the repolens package can be imported."""
    assert repolens is not None


def test_version_is_defined() -> None:
    """Verify that __version__ is a non-empty string."""
    assert hasattr(repolens, "__version__")
    assert isinstance(repolens.__version__, str)
    assert len(repolens.__version__) > 0


def test_subpackages_are_importable() -> None:
    """Verify that all architectural layer packages can be imported."""
    from repolens import ai, analyzers, api, application, cli, domain, infrastructure, reports

    subpackages = [domain, application, analyzers, ai, reports, infrastructure, api, cli]
    for pkg in subpackages:
        assert pkg is not None
