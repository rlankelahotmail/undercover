"""The UnderCover Agent."""

import json
import os
import uuid
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv(override=True)

BACKEND_URL = "http://127.0.0.1:8000"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"


def backend() -> httpx.Client:
    """Return a client for the UnderCover backend."""
    return httpx.Client(base_url=BACKEND_URL, timeout=30)


def send(method: str, path: str, body: dict[str, Any] | None = None) -> httpx.Response:
    """Send one request to the backend."""
    with backend() as client:
        return client.request(method, path, json=body)


def api(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    """Call the backend and return its answer, raising if it refuses."""
    response = send(method, path, body)
    response.raise_for_status()
    return response.json()


def answer(method: str, path: str, body: dict[str, Any] | None = None) -> str:
    """Call the backend for a tool, so a refusal comes back for the agent to read."""
    response = send(method, path, body)
    if response.is_client_error:
        return json.dumps({"refused": response.json()["detail"]})
    response.raise_for_status()
    return response.text


@tool
def get_claim(claim_id: str) -> str:
    """Get a claim in full: the customer's story, the items claimed and documents."""
    return answer("GET", f"/api/claims/{claim_id}")


@tool
def get_policy(policy_id: str) -> str:
    """Get a policy: its plan, add-ons, purchase date, trip and travelers."""
    return answer("GET", f"/api/policies/{policy_id}")


@tool
def get_claim_history(customer_id: str) -> str:
    """Get a customer's earlier claims."""
    return answer("GET", f"/api/customers/{customer_id}/history")


@tool
def record_decision(
    claim_id: str,
    outcome: Literal["approve", "decline", "refer"],
    payout: float,
    reason: str,
    policy_section: str,
) -> str:
    """Record the decision on a claim, with a payout of 0 unless it is approved."""
    decision = {
        "outcome": outcome,
        "payout": payout,
        "reason": reason,
        "policy_section": policy_section,
    }
    return answer("POST", f"/api/claims/{claim_id}/decision", decision)


@tool
def pay_claim(claim_id: str, amount: float) -> str:
    """Pay an approved claim the payout recorded in its decision."""
    return answer("POST", f"/api/claims/{claim_id}/payment", {"amount": amount})


TOOLS = [get_claim, get_policy, get_claim_history, record_decision, pay_claim]


def model() -> ChatOpenAI:
    """Return the model named in MODEL_NAME, or GPT-6 Luna by default."""
    name = os.getenv("MODEL_NAME")
    return ChatOpenAI(
        model=name or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if name else "low",
    )


def instructions() -> str:
    """Return the agent's instructions from the backend."""
    return api("GET", "/api/instructions")["instructions"]


def steps(message: BaseMessage) -> list[dict[str, str]]:
    """Turn one of the agent's messages into the steps the dashboard shows."""
    if isinstance(message, ToolMessage):
        return [{"kind": "result", "name": message.name or "", "content": message.text}]
    if not isinstance(message, AIMessage):
        return []
    said = [{"kind": "message", "name": "agent", "content": message.text}]
    calls = [
        {"kind": "call", "name": call["name"], "content": json.dumps(call["args"])}
        for call in message.tool_calls
    ]
    return (said if message.text else []) + calls


def run(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> str:
    """Run the agent on one claim, posting each step, and return its final reply."""
    agent = create_agent(llm or model(), tools=TOOLS, system_prompt=instructions())
    api("POST", f"/api/claims/{claim_id}/start")
    reply = ""
    for update in agent.stream(
        {"messages": [{"role": "user", "content": f"Decide claim {claim_id}."}]},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode="updates",
    ):
        for node in update.values():
            for message in node["messages"]:
                for step in steps(message):
                    path = f"/api/claims/{claim_id}/steps"
                    api("POST", path, {"thread_id": thread_id, **step})
                if isinstance(message, AIMessage):
                    reply = message.text
    return reply


def outcome(claim: dict[str, Any]) -> str:
    """Say in one line what became of a claim."""
    status = claim["status"].replace("_", " ")
    decision = claim["decision"]
    if decision is None:
        return f"{claim['claim_id']}: no decision recorded, {status}"
    paid = ", paid" if claim["payment"] else ""
    return (
        f"{claim['claim_id']}: {decision['outcome']} ${decision['payout']:,.2f},"
        f" {status}{paid}"
    )


def work(claim_ids: list[str]) -> None:
    """Work the claims given, or every claim in the queue not yet decided."""
    if not claim_ids:
        queue = api("GET", "/api/claims")
        claim_ids = [
            claim["claim_id"]
            for claim in queue
            if claim["status"] in {"waiting", "in_progress"}
        ]
    for claim_id in claim_ids:
        run(claim_id, str(uuid.uuid4()))
        print(outcome(api("GET", f"/api/claims/{claim_id}")), flush=True)
