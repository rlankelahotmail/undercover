import pytest

from backend.seed import seed


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "test.db"))
    seed()
