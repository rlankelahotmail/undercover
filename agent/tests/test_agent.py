import json

import pytest
from fastapi.testclient import TestClient
from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from agent import main
from backend.main import app


class StubModel(GenericFakeChatModel):
    """A chat model that gives scripted replies in place of a real model."""

    def bind_tools(self, tools, **kwargs):
        return self


def calls(*scripted):
    """Script one model reply per tool call, then a final reply."""
    *tool_calls, final = scripted
    replies = [
        AIMessage(
            content="",
            tool_calls=[{"name": name, "args": args, "id": str(number)}],
        )
        for number, (name, args) in enumerate(tool_calls)
    ]
    return StubModel(messages=iter([*replies, AIMessage(content=final)]))


def decision(claim_id, outcome, payout):
    return {
        "claim_id": claim_id,
        "outcome": outcome,
        "payout": payout,
        "reason": "The claim is covered.",
        "policy_section": "Section 3, Trip Delay",
    }


@pytest.fixture(autouse=True)
def backend(monkeypatch):
    monkeypatch.setattr(main, "backend", lambda: TestClient(app))


@pytest.fixture
def client():
    return TestClient(app)


def test_a_run_reads_decides_and_pays(client):
    stub = calls(
        ("get_claim", {"claim_id": "CLM-1001"}),
        ("get_policy", {"policy_id": "POL-2001"}),
        ("get_claim_history", {"customer_id": "CUS-3001"}),
        ("record_decision", decision("CLM-1001", "approve", 420)),
        ("pay_claim", {"claim_id": "CLM-1001", "amount": 420}),
        "Approved CLM-1001 for $420.00.",
    )
    assert main.run("CLM-1001", "thread-1", stub) == "Approved CLM-1001 for $420.00."
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "decided"
    assert claim["payment"]["amount"] == 420
    steps = client.get("/api/claims/CLM-1001/steps").json()
    assert [(step["kind"], step["name"]) for step in steps] == [
        ("call", "get_claim"),
        ("result", "get_claim"),
        ("call", "get_policy"),
        ("result", "get_policy"),
        ("call", "get_claim_history"),
        ("result", "get_claim_history"),
        ("call", "record_decision"),
        ("result", "record_decision"),
        ("call", "pay_claim"),
        ("result", "pay_claim"),
        ("message", "agent"),
    ]
    assert {step["thread_id"] for step in steps} == {"thread-1"}
    assert json.loads(steps[2]["content"]) == {"policy_id": "POL-2001"}
    assert json.loads(steps[3]["content"])["plan"] == "premium"


def test_the_backend_refuses_a_payment_over_the_limit(client):
    stub = calls(
        ("record_decision", decision("CLM-1003", "approve", 1250)),
        ("pay_claim", {"claim_id": "CLM-1003", "amount": 1250}),
        "Approved CLM-1003 for $1,250.00.",
    )
    main.run("CLM-1003", "thread-2", stub)
    claim = client.get("/api/claims/CLM-1003").json()
    assert claim["status"] == "waiting_for_sign_off"
    assert claim["payment"] is None
    result = client.get("/api/claims/CLM-1003/steps").json()[3]
    assert result["name"] == "pay_claim"
    assert "needs a handler's sign-off" in json.loads(result["content"])["refused"]


def test_the_system_prompt_comes_from_the_backend(client, monkeypatch):
    prompts = []

    def spy(model, tools, system_prompt):
        prompts.append(system_prompt)
        return create_agent(model, tools=tools, system_prompt=system_prompt)

    monkeypatch.setattr(main, "create_agent", spy)
    main.run("CLM-1001", "thread-3", calls("Nothing to do."))
    assert prompts == [client.get("/api/instructions").json()["instructions"]]


def test_work_takes_only_claims_not_yet_decided(client, monkeypatch, capsys):
    runs = []
    monkeypatch.setattr(main, "run", lambda claim_id, thread_id: runs.append(thread_id))
    client.post("/api/claims/CLM-1001/start")
    client.post(
        "/api/claims/CLM-1001/decision", json=decision("CLM-1001", "decline", 0)
    )
    client.post("/api/claims/CLM-1003/start")
    client.post(
        "/api/claims/CLM-1003/decision", json=decision("CLM-1003", "approve", 1250)
    )
    client.post("/api/claims/CLM-1004/start")
    main.work([])
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 23
    assert lines[0] == "CLM-1002: no decision recorded, waiting"
    assert "CLM-1004: no decision recorded, in progress" in lines
    assert len(set(runs)) == 23


def test_work_on_one_claim(monkeypatch, capsys):
    real_run = main.run

    def run(claim_id, thread_id):
        stub = calls(
            ("record_decision", decision(claim_id, "approve", 420)),
            ("pay_claim", {"claim_id": claim_id, "amount": 420}),
            "Approved.",
        )
        real_run(claim_id, thread_id, stub)

    monkeypatch.setattr(main, "run", run)
    main.work(["CLM-1001"])
    assert capsys.readouterr().out == "CLM-1001: approve $420.00, decided, paid\n"


def test_model_name(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    assert main.model().model_name == "openai/gpt-6-luna"
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    assert main.model().model_name == "openrouter/free"
