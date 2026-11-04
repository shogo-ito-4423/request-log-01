from unittest.mock import patch

import pytest

from app.database import make_engine


@pytest.mark.parametrize(
    ("database_url", "expected_connect_args"),
    [
        ("sqlite:///test.db", {"check_same_thread": False, "timeout": 10}),
        ("sqlite+pysqlite:///test.db", {"check_same_thread": False, "timeout": 10}),
        ("postgresql://localhost/test", {}),
        ("postgresql+psycopg://localhost/test", {}),
    ],
)
def test_make_engine_uses_backend_specific_connect_args(database_url, expected_connect_args):
    with patch("app.database.create_engine") as create_engine_mock:
        engine = make_engine(database_url)

    create_engine_mock.assert_called_once()
    args, kwargs = create_engine_mock.call_args
    assert args == (database_url,)
    assert kwargs.get("connect_args", {}) == expected_connect_args
    assert engine is create_engine_mock.return_value
