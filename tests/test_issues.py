from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_read_list_and_update(client):
    assert client.get("/issues").json() == []
    response = client.post(
        "/issues", json={"title": "  月次集計を自動化  ", "description": "転記を減らす"}
    )
    assert response.status_code == 201
    issue = response.json()
    assert response.headers["location"] == f"/issues/{issue['id']}"
    assert issue["title"] == "月次集計を自動化"
    assert issue["status"] == "open"
    assert issue["priority"] == "medium"
    assert issue["assignee"] is None
    assert datetime.fromisoformat(issue["created_at"]).utcoffset().total_seconds() == 0
    assert client.get(f"/issues/{issue['id']}").json() == issue
    assert client.get("/issues").json() == [issue]

    updated = client.patch(
        f"/issues/{issue['id']}",
        json={"status": "in_progress", "priority": "high", "assignee": "担当A"},
    )
    assert updated.status_code == 200
    data = updated.json()
    assert data["status"] == "in_progress"
    assert data["priority"] == "high"
    assert data["assignee"] == "担当A"
    assert data["description"] == issue["description"]
    assert data["title"] == issue["title"]
    assert data["created_at"] == issue["created_at"]
    assert datetime.fromisoformat(data["updated_at"]) >= datetime.fromisoformat(issue["updated_at"])
    assert client.get(f"/issues/{issue['id']}").json() == data


def test_clear_assignee_and_update_content(client):
    issue = client.post("/issues", json={"title": "旧題", "assignee": "担当A"}).json()
    updated = client.patch(
        f"/issues/{issue['id']}",
        json={"title": "新題", "description": "", "status": "done", "assignee": None},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "新題"
    assert updated.json()["description"] == ""
    assert updated.json()["status"] == "done"
    assert updated.json()["assignee"] is None


@pytest.mark.parametrize("method", ["get", "patch"])
def test_missing_issue_returns_404(client, method):
    kwargs = {"json": {"status": "done"}} if method == "patch" else {}
    response = getattr(client, method)("/issues/999", **kwargs)
    assert response.status_code == 404
    assert response.json() == {"detail": "Issue not found"}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": ""},
        {"title": " \t\n"},
        {"title": None},
        {"title": 123},
        {"title": "x" * 201},
        {"title": "x", "description": "x" * 10001},
        {"title": "x", "status": "closed"},
        {"title": "x", "priority": "urgent"},
        {"title": "x", "assignee": " "},
        {"title": "x", "assignee": "x" * 101},
        {"title": "x", "unexpected": "value"},
        {"title": "x", "description": None},
    ],
)
def test_invalid_creation_is_rejected_without_writes(client, payload):
    assert client.post("/issues", json=payload).status_code == 422
    assert client.get("/issues").json() == []


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": " "},
        {"title": None},
        {"description": None},
        {"status": None},
        {"priority": None},
        {"status": "closed"},
        {"priority": "urgent"},
        {"assignee": ""},
        {"id": 22},
        {"created_at": "2026-10-12"},
        {"title": "x" * 201},
        {"description": "x" * 10001},
    ],
)
def test_invalid_patch_preserves_record(client, payload):
    original = client.post("/issues", json={"title": "原本"}).json()
    url = f"/issues/{original['id']}"
    assert client.patch(url, json=payload).status_code == 422
    assert client.get(url).json() == original


@pytest.mark.parametrize("identifier", ["0", "-1", "abc", "1.5"])
@pytest.mark.parametrize("method", ["get", "patch"])
def test_invalid_id(client, identifier, method):
    kwargs = {"json": {"status": "done"}} if method == "patch" else {}
    assert getattr(client, method)(f"/issues/{identifier}", **kwargs).status_code == 422


def test_pagination_has_stable_order(client):
    ids = [client.post("/issues", json={"title": str(i)}).json()["id"] for i in range(4)]
    response = client.get("/issues?limit=2&offset=1")
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == ids[1:3]
    assert client.get("/issues?offset=99").json() == []


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "limit=abc"])
def test_invalid_pagination(client, query):
    assert client.get(f"/issues?{query}").status_code == 422


def test_data_survives_app_recreation(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'persistent.db'}"
    with TestClient(create_app(database_url)) as first:
        created = first.post("/issues", json={"title": "再起動後も保持"}).json()
        saved = first.patch(f"/issues/{created['id']}", json={"status": "done"}).json()
    with TestClient(create_app(database_url)) as second:
        assert second.get(f"/issues/{saved['id']}").json() == saved


def test_environment_database_url(tmp_path, monkeypatch):
    database = tmp_path / "environment.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database}")
    with TestClient(create_app()) as client:
        assert client.post("/issues", json={"title": "環境変数"}).status_code == 201
    assert database.exists()


def test_health_reports_unavailable_database(client):
    from sqlalchemy.exc import OperationalError

    from app.database import get_session

    class UnavailableSession:
        def execute(self, statement):
            raise OperationalError("SELECT 1", {}, Exception("private connection details"))

    client.app.dependency_overrides[get_session] = lambda: UnavailableSession()
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}


def test_openapi_documents_all_endpoints(client):
    schema = client.get("/openapi.json").json()
    assert set(schema["paths"]) == {"/health", "/issues", "/issues/{issue_id}"}
    assert schema["paths"]["/issues"]["post"]["responses"].get("201")
