import json

import pytest

from backend import db

STEP = {"thread_id": "thread-1", "kind": "call", "name": "get_claim", "content": "{}"}


def decide(client, claim_id, outcome, payout):
    client.post(f"/api/claims/{claim_id}/start")
    return client.post(
        f"/api/claims/{claim_id}/decision",
        json={
            "outcome": outcome,
            "payout": payout,
            "reason": "The delay was covered.",
            "policy_section": "Section 3, Trip Delay",
        },
    )


def pay(client, claim_id, amount):
    return client.post(f"/api/claims/{claim_id}/payment", json={"amount": amount})


def sign_off(client, claim_id, handler_id):
    return client.post(
        f"/api/claims/{claim_id}/sign-off", json={"handler_id": handler_id}
    )


def test_start(client):
    assert client.post("/api/claims/CLM-1001/start").json()["status"] == "in_progress"
    assert client.post("/api/claims/CLM-1001/start").status_code == 200
    assert client.post("/api/claims/CLM-9999/start").status_code == 404


def test_a_decided_claim_cannot_be_started(client):
    decide(client, "CLM-1001", "decline", 0)
    response = client.post("/api/claims/CLM-1001/start")
    assert response.status_code == 409
    assert response.json()["detail"] == "Claim CLM-1001 can't be started: it is decided"


def test_steps(client):
    client.post("/api/claims/CLM-1001/start")
    first = client.post("/api/claims/CLM-1001/steps", json=STEP).json()
    client.post("/api/claims/CLM-1001/steps", json=STEP | {"kind": "result"})
    steps = client.get("/api/claims/CLM-1001/steps").json()
    assert [step["kind"] for step in steps] == ["call", "result"]
    assert steps[0] == first
    assert first["thread_id"] == "thread-1"
    assert first["name"] == "get_claim"
    client.post("/api/claims/CLM-1001/start")
    assert client.get("/api/claims/CLM-1001/steps").json() == []


def test_steps_for_an_unknown_claim(client):
    assert client.post("/api/claims/CLM-9999/steps", json=STEP).status_code == 404
    assert client.get("/api/claims/CLM-9999/steps").status_code == 404


def test_approve(client):
    claim = decide(client, "CLM-1001", "approve", 420).json()
    assert claim["status"] == "decided"
    assert claim["decision"]["outcome"] == "approve"
    assert claim["decision"]["payout"] == 420
    assert claim["decision"]["reason"] == "The delay was covered."
    assert claim["decision"]["policy_section"] == "Section 3, Trip Delay"
    assert claim["payment"] is None


def test_one_decision_per_claim(client):
    decide(client, "CLM-1001", "approve", 420)
    response = decide(client, "CLM-1001", "decline", 0)
    assert response.status_code == 409


def test_a_waiting_claim_cannot_take_a_decision(client):
    response = client.post(
        "/api/claims/CLM-1001/decision",
        json={
            "outcome": "refer",
            "payout": 0,
            "reason": "A document is missing.",
            "policy_section": "Section 11, How to claim",
        },
    )
    assert response.status_code == 409


@pytest.mark.parametrize(
    ("outcome", "payout"), [("decline", 10), ("refer", 10), ("approve", 0)]
)
def test_the_payout_must_fit_the_outcome(client, outcome, payout):
    assert decide(client, "CLM-1001", outcome, payout).status_code == 422


def test_pay(client):
    decide(client, "CLM-1001", "approve", 420)
    claim = pay(client, "CLM-1001", 420).json()
    assert claim["payment"]["amount"] == 420
    assert client.get("/api/claims").json()[0]["paid"] is True


def test_pay_only_once(client):
    decide(client, "CLM-1001", "approve", 420)
    pay(client, "CLM-1001", 420)
    response = pay(client, "CLM-1001", 420)
    assert response.status_code == 409
    assert response.json()["detail"] == "Claim CLM-1001 is already paid"


def test_pay_only_the_approved_amount(client):
    decide(client, "CLM-1001", "approve", 420)
    response = pay(client, "CLM-1001", 500)
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Claim CLM-1001 was approved for $420.00, so it can't be paid $500.00"
    )
    assert client.get("/api/claims/CLM-1001").json()["payment"] is None


@pytest.mark.parametrize("outcome", ["decline", "refer", None])
def test_pay_only_an_approved_claim(client, outcome):
    if outcome:
        decide(client, "CLM-1001", outcome, 0)
    response = pay(client, "CLM-1001", 420)
    assert response.status_code == 409
    assert client.get("/api/claims/CLM-1001").json()["payment"] is None


def test_a_payout_over_the_limit_waits_for_sign_off(client):
    claim = decide(client, "CLM-1003", "approve", 1250).json()
    assert claim["status"] == "waiting_for_sign_off"
    response = pay(client, "CLM-1003", 1250)
    assert response.status_code == 409
    assert "needs a handler's sign-off" in response.json()["detail"]
    assert client.get("/api/claims/CLM-1003").json()["payment"] is None


def test_a_payout_at_the_limit_needs_no_sign_off(client):
    assert decide(client, "CLM-1003", "approve", 1000).json()["status"] == "decided"
    assert pay(client, "CLM-1003", 1000).status_code == 200


def test_sign_off_pays(client):
    decide(client, "CLM-1003", "approve", 1250)
    claim = sign_off(client, "CLM-1003", "HND-01").json()
    assert claim["status"] == "decided"
    assert claim["sign_off"]["handler_name"] == "Dana Whitfield"
    assert claim["payment"]["amount"] == 1250


def test_sign_off_only_a_claim_waiting_for_it(client):
    decide(client, "CLM-1001", "approve", 420)
    assert sign_off(client, "CLM-1001", "HND-01").status_code == 409
    assert client.get("/api/claims/CLM-1001").json()["sign_off"] is None


def test_sign_off_by_an_unknown_handler(client):
    decide(client, "CLM-1003", "approve", 1250)
    assert sign_off(client, "CLM-1003", "HND-99").status_code == 404


def test_sign_off_only_by_a_handler_who_may(client):
    handler = {
        "handler_id": "HND-04",
        "name": "Sam Trainee",
        "role": "Trainee",
        "email": "sam.trainee@undercover.example",
        "can_approve_over_limit": False,
    }
    with db.connect() as connection:
        connection.execute(
            "INSERT INTO handlers VALUES (?, ?)", ("HND-04", json.dumps(handler))
        )
    decide(client, "CLM-1003", "approve", 1250)
    response = sign_off(client, "CLM-1003", "HND-04")
    assert response.status_code == 403
    claim = client.get("/api/claims/CLM-1003").json()
    assert claim["status"] == "waiting_for_sign_off"
    assert claim["payment"] is None


def test_the_queue_shows_decisions_and_payments(client):
    decide(client, "CLM-1001", "approve", 420)
    pay(client, "CLM-1001", 420)
    decide(client, "CLM-1002", "decline", 0)
    first, second = client.get("/api/claims").json()[:2]
    assert (first["outcome"], first["payout"], first["paid"]) == ("approve", 420, True)
    assert (second["outcome"], second["payout"], second["paid"]) == (
        "decline",
        0,
        False,
    )
