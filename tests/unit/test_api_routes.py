"""Unit tests for API routes using FastAPI TestClient."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from repolens.api.app import create_app
from repolens.application.analysis_service import AnalysisService
from repolens.domain.persistence import AnalysisRecord
from repolens.domain.repository import RepositoryInfo, RepositoryWorkspace


class FakeStore:
    """In-memory store for testing."""

    def __init__(self) -> None:
        self._records: dict[str, AnalysisRecord] = {}

    def save(self, record: AnalysisRecord) -> None:
        self._records[record.id] = record

    def update(self, record: AnalysisRecord) -> None:
        self._records[record.id] = record

    def get(self, analysis_id: str) -> AnalysisRecord | None:
        return self._records.get(analysis_id)

    def list_recent(self, limit: int = 20) -> list[AnalysisRecord]:
        records = sorted(
            self._records.values(), key=lambda r: r.created_at, reverse=True
        )
        return records[:limit]


class FakeSource:
    """Fake repository source."""

    def __init__(self, workspace: RepositoryWorkspace) -> None:
        self._workspace = workspace

    def acquire(self, source: str) -> RepositoryWorkspace:
        return self._workspace


@pytest.fixture
def workspace(tmp_path: Path) -> RepositoryWorkspace:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "README.md").write_text("# Test")
    (repo_dir / "main.py").write_text("print('hello')")
    info = RepositoryInfo(
        owner="test-owner",
        name="test-repo",
        url="https://github.com/test-owner/test-repo",
        clone_url="https://github.com/test-owner/test-repo.git",
    )
    return RepositoryWorkspace(root=repo_dir, info=info)


@pytest.fixture
def service(workspace: RepositoryWorkspace) -> AnalysisService:
    source = FakeSource(workspace)
    store = FakeStore()
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


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"


class TestCreateAnalysis:
    def test_successful_analysis(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/analyses",
            json={
                "repository_url": "https://github.com/test-owner/test-repo",
                "include_ai_review": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["repository_name"] == "test-owner/test-repo"
        assert data["analysis_id"] is not None

    def test_invalid_url(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/analyses",
            json={"repository_url": "not-a-url"},
        )
        assert resp.status_code == 422

    def test_invalid_report_format(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/analyses",
            json={
                "repository_url": "https://github.com/test-owner/test-repo",
                "report_format": "pdf",
            },
        )
        assert resp.status_code == 422

    def test_empty_url_rejected(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/analyses",
            json={"repository_url": ""},
        )
        assert resp.status_code == 422


class TestGetAnalysis:
    def test_get_existing_analysis(self, client: TestClient) -> None:
        # Create first
        create_resp = client.post(
            "/api/v1/analyses",
            json={
                "repository_url": "https://github.com/test-owner/test-repo",
                "include_ai_review": False,
            },
        )
        analysis_id = create_resp.json()["analysis_id"]

        resp = client.get(f"/api/v1/analyses/{analysis_id}")
        assert resp.status_code == 200
        assert resp.json()["analysis_id"] == analysis_id

    def test_get_missing_analysis(self, client: TestClient) -> None:
        resp = client.get("/api/v1/analyses/nonexistent")
        assert resp.status_code == 422  # ValidationError maps to 422


class TestListAnalyses:
    def test_empty_list(self, client: TestClient) -> None:
        resp = client.get("/api/v1/analyses")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_after_create(self, client: TestClient) -> None:
        client.post(
            "/api/v1/analyses",
            json={
                "repository_url": "https://github.com/test-owner/test-repo",
                "include_ai_review": False,
            },
        )
        resp = client.get("/api/v1/analyses")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1


class TestGetFindings:
    def test_findings_endpoint(self, client: TestClient) -> None:
        create_resp = client.post(
            "/api/v1/analyses",
            json={
                "repository_url": "https://github.com/test-owner/test-repo",
                "include_ai_review": False,
            },
        )
        analysis_id = create_resp.json()["analysis_id"]

        resp = client.get(f"/api/v1/analyses/{analysis_id}/findings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["analysis_id"] == analysis_id
        assert isinstance(data["findings"], list)


class TestGetReport:
    def test_html_report(self, client: TestClient) -> None:
        create_resp = client.post(
            "/api/v1/analyses",
            json={
                "repository_url": "https://github.com/test-owner/test-repo",
                "include_ai_review": False,
            },
        )
        analysis_id = create_resp.json()["analysis_id"]

        resp = client.get(f"/api/v1/analyses/{analysis_id}/report?format=html")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/html")
        content = resp.text
        assert "<html" in content.lower() or "<!doctype" in content.lower()

    def test_json_report(self, client: TestClient) -> None:
        create_resp = client.post(
            "/api/v1/analyses",
            json={
                "repository_url": "https://github.com/test-owner/test-repo",
                "include_ai_review": False,
            },
        )
        analysis_id = create_resp.json()["analysis_id"]

        resp = client.get(f"/api/v1/analyses/{analysis_id}/report?format=json")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")
        data = resp.json()
        assert data["format"] == "json"
        assert "content" in data
        assert isinstance(data["content"], str)

    def test_markdown_report(self, client: TestClient) -> None:
        create_resp = client.post(
            "/api/v1/analyses",
            json={
                "repository_url": "https://github.com/test-owner/test-repo",
                "include_ai_review": False,
            },
        )
        analysis_id = create_resp.json()["analysis_id"]

        resp = client.get(f"/api/v1/analyses/{analysis_id}/report?format=markdown")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")
        data = resp.json()
        assert data["format"] == "markdown"
        assert "content" in data
        assert isinstance(data["content"], str)

    def test_invalid_format(self, client: TestClient) -> None:
        create_resp = client.post(
            "/api/v1/analyses",
            json={
                "repository_url": "https://github.com/test-owner/test-repo",
                "include_ai_review": False,
            },
        )
        analysis_id = create_resp.json()["analysis_id"]

        resp = client.get(f"/api/v1/analyses/{analysis_id}/report?format=pdf")
        assert resp.status_code == 422
