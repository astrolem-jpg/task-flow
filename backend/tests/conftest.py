import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import migrate


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("TASKFLOW_DB", str(tmp_path / "test.db"))
    migrate()
    with TestClient(app) as c:
        yield c
