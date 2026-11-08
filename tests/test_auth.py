import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from app.auth import load_users
from app.main import create_app
from app.models import Issue


def headers(name):
    return {"Authorization": f"Bearer test-{name}"}


@pytest.mark.parametrize("authorization", ["", "Basic dGVzdA==", "Bearer invalid", "Bearer"])
def test_unauthenticated_requests(client, authorization):
    for method, path, payload in [
        ("get", "/issues", None),
        ("get", "/issues/1", None),
        ("post", "/issues", {"title": "blocked"}),
        ("patch", "/issues/1", {"title": "blocked"}),
        ("delete", "/issues/1", None),
    ]:
        response = client.request(
            method, path, json=payload, headers={"Authorization": authorization}
        )
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
    assert client.get("/issues").json() == []
    assert client.get("/health", headers={"Authorization": ""}).status_code == 200


def test_owner_and_admin_permissions(client):
    alice = client.post("/issues", json={"title": "alice"}).json()
    bob = client.post("/issues", json={"title": "bob"}, headers=headers("bob")).json()
    assert alice["owner_id"] == "alice"
    assert bob["owner_id"] == "bob"
    path = f"/issues/{alice['id']}"
    assert client.get(path, headers=headers("bob")).json() == alice
    assert client.get("/issues", headers=headers("bob")).json() == [alice, bob]
    assert client.patch(path, json={"title": "attack"}, headers=headers("bob")).status_code == 403
    assert client.delete(path, headers=headers("bob")).status_code == 403
    assert client.get(path).json() == alice
    assert client.patch(path, json={"assignee": "bob"}).status_code == 200
    # Assignment is not ownership and cannot grant permission.
    assert client.delete(path, headers=headers("bob")).status_code == 403
    assert (
        client.patch(path, json={"title": "admin"}, headers=headers("manager")).status_code == 200
    )
    assert client.get(path).json()["owner_id"] == "alice"
    assert client.delete(path, headers=headers("manager")).status_code == 204
    assert client.get(f"/issues/{bob['id']}").json() == bob
    assert client.delete(f"/issues/{bob['id']}", headers=headers("bob")).status_code == 204
    created = client.post("/issues", json={"title": "admin"}, headers=headers("manager"))
    assert created.status_code == 201
    assert created.json()["owner_id"] == "manager"


def test_cannot_forge_owner_or_role(client):
    for field in ("owner_id", "role", "user_id"):
        assert client.post("/issues", json={"title": "x", field: "manager"}).status_code == 422
    original = client.post("/issues", json={"title": "x"}).json()
    path = f"/issues/{original['id']}"
    assert client.patch(path, json={"owner_id": "bob"}).status_code == 422
    assert client.get(path).json() == original


def test_legacy_records_require_admin(client):
    original = client.post("/issues", json={"title": "legacy"}).json()
    with client.app.state.engine.begin() as connection:
        connection.execute(update(Issue).values(owner_id=None))
    path = f"/issues/{original['id']}"
    assert client.get(path).json()["owner_id"] is None
    assert client.patch(path, json={"title": "x"}).status_code == 403
    assert client.delete(path).status_code == 403
    assert (
        client.patch(path, json={"title": "managed"}, headers=headers("manager")).status_code == 200
    )
    assert client.delete(path, headers=headers("manager")).status_code == 204


@pytest.mark.parametrize("raw", [None, "", "[]", "private-invalid", "{}", '[{"role":"root"}]'])
def test_invalid_settings_fail_closed(monkeypatch, raw):
    if raw is None:
        monkeypatch.delenv("AUTH_USERS_JSON")
    else:
        monkeypatch.setenv("AUTH_USERS_JSON", raw)
    with pytest.raises(ValueError, match="unique users and token hashes") as error:
        with TestClient(create_app()):
            pass
    assert "private-invalid" not in str(error.value)


@pytest.mark.parametrize("duplicate", ["user_id", "token_sha256"])
def test_duplicate_settings_rejected(monkeypatch, duplicate):
    users = [user.model_dump() for user in load_users()]
    users[1][duplicate] = users[0][duplicate]
    monkeypatch.setenv("AUTH_USERS_JSON", json.dumps(users))
    with pytest.raises(ValueError):
        load_users()


def test_revoked_token_is_rejected_after_restart(client, monkeypatch):
    users = [user.model_dump() for user in load_users() if user.user_id != "alice"]
    monkeypatch.setenv("AUTH_USERS_JSON", json.dumps(users))
    with TestClient(create_app(str(client.app.state.engine.url))) as restarted:
        assert restarted.get("/issues", headers=headers("alice")).status_code == 401
        assert restarted.get("/issues", headers=headers("bob")).status_code == 200


def test_openapi_security(client):
    paths = client.get("/openapi.json").json()["paths"]
    for path in ("/issues", "/issues/{issue_id}"):
        for operation in paths[path].values():
            assert operation["security"] == [{"HTTPBearer": []}]
    assert "security" not in paths["/health"]["get"]
