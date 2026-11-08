import hashlib
import json

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def migrate():
    def upgrade(database_url):
        config = Config("alembic.ini")
        config.attributes["database_url"] = database_url
        command.upgrade(config, "head")

    return upgrade


@pytest.fixture
def client(tmp_path, migrate):
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    migrate(database_url)
    with TestClient(
        create_app(database_url), headers={"Authorization": "Bearer test-alice"}
    ) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def auth_settings(monkeypatch):
    users = [
        {
            "user_id": name,
            "role": role,
            "token_sha256": hashlib.sha256(f"test-{name}".encode()).hexdigest(),
        }
        for name, role in [("alice", "user"), ("bob", "user"), ("manager", "admin")]
    ]
    monkeypatch.setenv("AUTH_USERS_JSON", json.dumps(users))
