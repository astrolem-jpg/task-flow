import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import migrate, signup_and_login


@pytest.fixture(autouse=True)
def session_secret(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret-not-real")


@pytest.fixture
def db_ready(tmp_path, monkeypatch):
    """임시 DB를 만들고 Alembic revision을 모두 적용한다. 실제 DB는 쓰지 않는다."""
    monkeypatch.setenv("TASKFLOW_DB", str(tmp_path / "test.db"))
    migrate()


@pytest.fixture
def anon_client(db_ready):
    """로그인하지 않은 클라이언트."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client(db_ready):
    """가입하고 로그인한 클라이언트."""
    with TestClient(app) as c:
        signup_and_login(c)
        yield c
