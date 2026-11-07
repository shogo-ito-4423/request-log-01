import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.database import make_engine
from app.main import create_app


def test_postgresql_crud(migrate):
    url = os.getenv("TEST_CRUD_DATABASE_URL")
    if not url:
        pytest.skip("Run compose.integration.yaml for PostgreSQL CRUD verification")
    engine = make_engine(url)
    try:
        assert engine.dialect.name == "postgresql"
        assert inspect(engine).get_table_names() == [], "Verification requires an empty database"
    finally:
        engine.dispose()
    migrate(url)

    with TestClient(create_app(url)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/issues").json() == []
        response = client.post("/issues", json={"title": "保持する要望"})
        assert response.status_code == 201
        kept = response.json()
        response = client.post(
            "/issues", json={"title": "  改善要望  ", "description": "PostgreSQLで検証"}
        )
        assert response.status_code == 201
        target = response.json()
        url = f"/issues/{target['id']}"
        assert response.headers["location"] == url
        assert target["title"] == "改善要望"
        assert target["status"] == "open"
        assert target["priority"] == "medium"
        assert target["assignee"] is None
        detail = client.get(url)
        assert detail.status_code == 200
        assert detail.json() == target
        listing = client.get("/issues")
        assert listing.status_code == 200
        assert listing.json() == [kept, target]

        updated = client.patch(url, json={"status": "done", "assignee": "担当A"})
        assert updated.status_code == 200
        saved = updated.json()
        assert saved == target | {
            "status": "done",
            "assignee": "担当A",
            "updated_at": saved["updated_at"],
        }
        assert client.get(url).json() == saved
        assert client.get("/issues?status=done").json() == [saved]
        invalid = client.patch(url, json={"title": "変更されない", "status": "invalid"})
        assert invalid.status_code == 422
        assert client.get(url).json() == saved
        assert client.post("/issues", json={"title": " "}).status_code == 422
        assert client.get("/issues").json() == [kept, saved]

        missing_url = f"/issues/{max(kept['id'], target['id']) + 1}"
        for method in ("get", "patch", "delete"):
            kwargs = {"json": {"status": "done"}} if method == "patch" else {}
            missing = getattr(client, method)(missing_url, **kwargs)
            assert missing.status_code == 404
            assert missing.json() == {"detail": "Issue not found"}
        deleted = client.delete(url)
        assert deleted.status_code == 204
        assert deleted.content == b""
        for response in (client.get(url), client.delete(url)):
            assert response.status_code == 404
            assert response.json() == {"detail": "Issue not found"}
        assert client.get(f"/issues/{kept['id']}").json() == kept
        assert client.get("/issues").json() == [kept]
