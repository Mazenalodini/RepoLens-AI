"""Integration tests for the full API round-trip.

Tests the complete flow: POST analysis → GET analysis → GET findings → GET report.
Uses temporary SQLite database and mocked GitHub/AI dependencies.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from repolens.api.app import create_app
from repolens.application.analysis_service import AnalysisService
from repolens.domain.repository import RepositoryInfo, RepositoryWorkspace
from repolens.infrastructure.analysis_store import SQLiteAnalysisStore
from repolens.infrastructure.database import (
    create_db_engine,
    create_session_factory,
    create_tables,
)


class FakeSource:
    """Fake repository source for integration tests."""

    def __init__(self, workspace: RepositoryWorkspace) -> None:
        self._workspace = workspace

    def acquire(self, source: str) -> RepositoryWorkspace:
        return self._workspace


@pytest.fixture
def workspace(tmp_path: Path) -> RepositoryWorkspace:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "README.md").write_text("# Test Project\nA test project.")
    (repo_dir / "main.py").write_text("def hello():\n    return 'hello'\n")
    (repo_dir / "test_main.py").write_text("def test_hello():\n    assert True\n")
    (repo_dir / "pyproject.toml").write_text('[project]\nname = "test"\nversion = "1.0.0"\n')

    info = RepositoryInfo(
        owner="integ-owner",
        name="integ-repo",
        url="https://github.com/integ-owner/integ-repo",
        clone_url="https://github.com/integ-owner/integ-repo.git",
    )
    return RepositoryWorkspace(root=repo_dir, info=info)


@pytest.fixture
def service(workspace: RepositoryWorkspace, tmp_path: Path) -> AnalysisService:
    """Create AnalysisService backed by real SQLite."""
    db_path = tmp_path / "integration_test.db"
    engine = create_db_engine(f"sqlite:///{db_path}")
    create_tables(engine)
    factory = create_session_factory(engine)

    store = SQLiteAnalysisStore(factory)
    source = FakeSource(workspace)

    return AnalysisService(
        source=source,
        store=store,
        ai_provider=None,
        max_concurrent=2,
    )


@pytest.fixture
def client(service: AnalysisService) -> TestClient:
    app = create_app()
    from repolens.api.dependencies import get_analysis_service

    app.dependency_overrides[get_analysis_service] = lambda: service
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


class TestFullRoundTrip:
    """Tests the complete API workflow from POST to GET."""

    def test_post_get_findings_report(self, client: TestClient) -> None:
        # Step 1: Create analysis
        create_resp = client.post(
            "/api/v1/analyses",
            json={
                "repository_url": "https://github.com/integ-owner/integ-repo",
                "include_ai_review": False,
            },
        )
        assert create_resp.status_code == 200
        data = create_resp.json()
        analysis_id = data["analysis_id"]
        assert data["status"] == "completed"
        assert data["repository_name"] == "integ-owner/integ-repo"

        # Step 2: GET analysis
        get_resp = client.get(f"/api/v1/analyses/{analysis_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["analysis_id"] == analysis_id
        assert get_resp.json()["status"] == "completed"

        # Step 3: GET findings
        findings_resp = client.get(f"/api/v1/analyses/{analysis_id}/findings")
        assert findings_resp.status_code == 200
        findings_data = findings_resp.json()
        assert findings_data["analysis_id"] == analysis_id
        assert isinstance(findings_data["findings"], list)
        assert findings_data["total"] == len(findings_data["findings"])

        # Step 4: GET report (HTML)
        report_resp = client.get(
            f"/api/v1/analyses/{analysis_id}/report?format=html"
        )
        assert report_resp.status_code == 200
        assert report_resp.headers["content-type"].startswith("text/html")
        report_data = report_resp.text
        assert len(report_data) > 0
        assert "<html" in report_data.lower() or "<!doctype" in report_data.lower()

        # Step 5: GET report (JSON)
        json_resp = client.get(
            f"/api/v1/analyses/{analysis_id}/report?format=json"
        )
        assert json_resp.status_code == 200

        # Step 6: GET report (Markdown)
        md_resp = client.get(
            f"/api/v1/analyses/{analysis_id}/report?format=markdown"
        )
        assert md_resp.status_code == 200

    def test_list_analyses_after_creation(self, client: TestClient) -> None:
        # List should be empty initially
        list_resp = client.get("/api/v1/analyses")
        assert list_resp.status_code == 200
        assert list_resp.json() == []

        # Create analysis
        client.post(
            "/api/v1/analyses",
            json={
                "repository_url": "https://github.com/integ-owner/integ-repo",
                "include_ai_review": False,
            },
        )

        # List should have one entry
        list_resp = client.get("/api/v1/analyses")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1


class TestDashboard:
    """Tests the server-rendered HTML dashboard."""

    def test_dashboard_home(self, client: TestClient) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "RepoLens AI" in resp.text
        assert "New Analysis" in resp.text

    def test_dashboard_analysis_detail(self, client: TestClient) -> None:
        # Create analysis first
        create_resp = client.post(
            "/api/v1/analyses",
            json={
                "repository_url": "https://github.com/integ-owner/integ-repo",
                "include_ai_review": False,
            },
        )
        analysis_id = create_resp.json()["analysis_id"]

        resp = client.get(f"/dashboard/analyses/{analysis_id}")
        assert resp.status_code == 200
        assert "integ-owner/integ-repo" in resp.text

    def test_dashboard_analysis_not_found(self, client: TestClient) -> None:
        resp = client.get("/dashboard/analyses/nonexistent")
        assert resp.status_code == 404

    def test_dashboard_findings_page(self, client: TestClient) -> None:
        create_resp = client.post(
            "/api/v1/analyses",
            json={
                "repository_url": "https://github.com/integ-owner/integ-repo",
                "include_ai_review": False,
            },
        )
        analysis_id = create_resp.json()["analysis_id"]

        resp = client.get(f"/dashboard/analyses/{analysis_id}/findings")
        assert resp.status_code == 200
        assert "Findings" in resp.text

    def test_dashboard_report_page(self, client: TestClient) -> None:
        create_resp = client.post(
            "/api/v1/analyses",
            json={
                "repository_url": "https://github.com/integ-owner/integ-repo",
                "include_ai_review": False,
            },
        )
        analysis_id = create_resp.json()["analysis_id"]

        resp = client.get(f"/dashboard/analyses/{analysis_id}/report")
        assert resp.status_code == 200
        assert "Report" in resp.text


class TestAIDisabled:
    """Tests that AI-disabled flow works cleanly."""

    def test_ai_review_not_available(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/analyses",
            json={
                "repository_url": "https://github.com/integ-owner/integ-repo",
                "include_ai_review": False,
            },
        )
        data = resp.json()
        assert data["ai_review_available"] is False

    def test_dashboard_shows_ai_unavailable(self, client: TestClient) -> None:
        create_resp = client.post(
            "/api/v1/analyses",
            json={
                "repository_url": "https://github.com/integ-owner/integ-repo",
                "include_ai_review": False,
            },
        )
        analysis_id = create_resp.json()["analysis_id"]

        resp = client.get(f"/dashboard/analyses/{analysis_id}")
        assert resp.status_code == 200
        assert "not available" in resp.text.lower()
