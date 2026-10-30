import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.seed import seed


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "test.db"))
    seed()


@pytest.fixture
def client():
    return TestClient(app)
