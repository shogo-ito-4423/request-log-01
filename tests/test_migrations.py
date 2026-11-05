import os
from datetime import datetime

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.database import make_engine
from app.main import create_app
from app.models import Base, Issue


def test_migration_round_trip(tmp_path):
    # Only point this override at a new, dedicated, empty verification database.
    url = os.getenv("TEST_MIGRATION_DATABASE_URL", f"sqlite:///{tmp_path / 'migration.db'}")
    config = Config("alembic.ini")
    config.attributes["database_url"] = url
    engine = make_engine(url)
    try:
        assert inspect(engine).get_table_names() == [], "Verification requires an empty database"
        # API startup must not silently create the schema.
        with TestClient(create_app(url)):
            assert inspect(engine).get_table_names() == []

        for attempt in range(2):
            command.upgrade(config, "head")
            with engine.connect() as connection:
                context = MigrationContext.configure(
                    connection, opts={"compare_type": True, "compare_server_default": True}
                )
                assert context.get_current_revision() == "0001"
                assert compare_metadata(context, Base.metadata) == []
            inspector = inspect(engine)
            assert {c["name"] for c in inspector.get_check_constraints("issues")} == {
                "valid_title",
                "valid_status",
                "valid_priority",
            }
            valid = {
                "title": "migration",
                "description": "",
                "status": "open",
                "priority": "medium",
                "created_at": datetime(2026, 11, 5),
                "updated_at": datetime(2026, 11, 5),
            }
            for invalid in ({"title": " "}, {"status": "invalid"}, {"priority": "invalid"}):
                with pytest.raises(IntegrityError), engine.begin() as connection:
                    connection.execute(Issue.__table__.insert().values(valid | invalid))
            with TestClient(create_app(url)) as client:
                response = client.post("/issues", json={"title": "移行後の保存"})
                assert response.status_code == 201
                saved = response.json()
                assert client.get(f"/issues/{saved['id']}").json() == saved
                # A repeated upgrade at head must preserve data.
                command.upgrade(config, "head")
                assert client.get(f"/issues/{saved['id']}").json() == saved
            if attempt == 0:
                command.downgrade(config, "base")
                assert "issues" not in inspect(engine).get_table_names()
                with engine.connect() as connection:
                    assert MigrationContext.configure(connection).get_current_revision() is None
    finally:
        engine.dispose()
