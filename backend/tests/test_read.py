import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.main import app
from backend.seed import seed


def test_seed_says_what_it_loaded():
    assert seed() == "Seeded 25 claims, 50 policies, 49 customers and 3 handlers"


def test_startup_seeds_a_missing_database(tmp_path, monkeypatch):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "fresh.db"))
    assert not db.path().exists()
    with TestClient(app) as client:
        assert len(client.get("/api/claims").json()) == 25


def test_queue(client):
    claims = client.get("/api/claims").json()
    assert [claim["claim_id"] for claim in claims] == [
        f"CLM-{n}" for n in range(1001, 1026)
    ]
    assert {claim["status"] for claim in claims} == {"waiting"}
    assert claims[0] == {
        "claim_id": "CLM-1001",
        "customer_name": "Maya Patel",
        "claim_type": "trip_delay",
        "summary": "Flight home canceled by the airline, rebooked the next morning",
        "submitted_on": "2026-06-24",
        "amount_claimed": 420.0,
        "status": "waiting",
        "outcome": None,
        "payout": None,
        "paid": False,
    }


def test_claim(client):
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["story"].startswith("My flight home from Rome")
    assert len(claim["items"]) == 3
    assert len(claim["documents"]) == 4
    assert claim["status"] == "waiting"
    assert claim["decision"] is None
    assert claim["sign_off"] is None
    assert claim["payment"] is None


def test_policy(client):
    policy = client.get("/api/policies/POL-2001").json()
    assert policy["plan"] == "premium"
    assert policy["add_ons"] == []
    assert policy["trip"] == {
        "destination": "Rome, Italy",
        "departs_on": "2026-06-10",
        "returns_on": "2026-06-18",
        "trip_cost": 3100.0,
    }


def test_claim_history_leaves_out_contact_details(client):
    history = client.get("/api/customers/CUS-3001/history").json()
    assert history["name"] == "Maya Patel"
    assert [claim["claim_id"] for claim in history["previous_claims"]] == ["CLM-0412"]
    assert set(history) == {"customer_id", "name", "customer_since", "previous_claims"}


def test_handlers(client):
    handlers = client.get("/api/handlers").json()
    assert [handler["handler_id"] for handler in handlers] == [
        "HND-01",
        "HND-02",
        "HND-03",
    ]
    assert "email" not in handlers[0]


@pytest.mark.parametrize(
    "path",
    [
        "/api/claims/CLM-9999",
        "/api/policies/POL-9999",
        "/api/customers/CUS-9999/history",
    ],
)
def test_unknown_ids(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert response.json()["detail"].endswith("9999")


def test_instructions_come_with_the_policy_wording(client):
    instructions = client.get("/api/instructions").json()["instructions"]
    assert instructions.startswith("# The UnderCover Agent")
    assert "# UnderCover Travel Insurance: Policy Wording" in instructions
    assert "Version 2026.1" in instructions
    assert "Claims Handling Manual" not in instructions
