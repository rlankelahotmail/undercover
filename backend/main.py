"""The UnderCover backend."""

import json
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import NoReturn

from fastapi import FastAPI, HTTPException

from backend import db
from backend.models import (
    Claim,
    ClaimHistory,
    ClaimSummary,
    Decision,
    Handler,
    NewStep,
    Payment,
    Policy,
    SignOff,
    Step,
)
from backend.seed import seed

QUEUE = """
SELECT claims.record, claims.status,
    json_extract(customers.record, '$.name') AS customer_name,
    decisions.outcome, decisions.payout, payments.claim_id IS NOT NULL AS paid
FROM claims
JOIN customers ON customers.customer_id = claims.customer_id
LEFT JOIN decisions ON decisions.claim_id = claims.claim_id
LEFT JOIN payments ON payments.claim_id = claims.claim_id
ORDER BY claims.claim_id
"""

SIGN_OFF = """
SELECT handler_id, json_extract(handlers.record, '$.name') AS handler_name,
    signed_off_at
FROM sign_offs JOIN handlers USING (handler_id)
WHERE claim_id = ?
"""


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Create and seed the database on startup if it doesn't exist yet."""
    if not db.path().exists():
        seed()
    yield


app = FastAPI(title="UnderCover", lifespan=lifespan)


def find(connection: sqlite3.Connection, sql: str, key: str, what: str) -> sqlite3.Row:
    """Return the one row for key, or answer 404."""
    row = connection.execute(sql, (key,)).fetchone()
    if row is None:
        raise HTTPException(404, f"There is no {what} {key}")
    return row


def refuse(message: str) -> NoReturn:
    """Answer 409: the claim isn't in a state that allows this."""
    raise HTTPException(409, message)


def now() -> str:
    """Return the time now, in UTC."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def money(amount: float) -> str:
    """Format an amount in US dollars, such as $1,250.00."""
    return f"${amount:,.2f}"


def status_of(connection: sqlite3.Connection, claim_id: str) -> str:
    """Return where a claim stands, or answer 404."""
    sql = "SELECT status FROM claims WHERE claim_id = ?"
    return find(connection, sql, claim_id, "claim")["status"]


def set_status(connection: sqlite3.Connection, claim_id: str, status: str) -> None:
    """Move a claim to a new status."""
    connection.execute(
        "UPDATE claims SET status = ? WHERE claim_id = ?", (status, claim_id)
    )


def approval_limit(connection: sqlite3.Connection) -> float:
    """Return the largest payout that needs no handler's sign-off."""
    row = connection.execute("SELECT value FROM settings WHERE key = 'company'")
    return json.loads(row.fetchone()["value"])["payout_approval_limit"]


def pay(connection: sqlite3.Connection, claim_id: str, amount: float) -> None:
    """Pay a claim if the payment rule allows it, the only way a payment is made."""
    claim = load_claim(connection, claim_id)
    decision = claim.decision
    if decision is None or decision.outcome != "approve":
        refuse(f"Claim {claim_id} isn't approved, so it can't be paid")
    if amount != decision.payout:
        refuse(
            f"Claim {claim_id} was approved for {money(decision.payout)},"
            f" so it can't be paid {money(amount)}"
        )
    if claim.payment:
        refuse(f"Claim {claim_id} is already paid")
    limit = approval_limit(connection)
    if decision.payout > limit and claim.sign_off is None:
        refuse(
            f"Claim {claim_id}'s payout of {money(decision.payout)} is over"
            f" {money(limit)}, so it needs a handler's sign-off before it's paid"
        )
    connection.execute(
        "INSERT INTO payments VALUES (?, ?, ?)", (claim_id, amount, now())
    )


def optional(row: sqlite3.Row | None) -> dict[str, object] | None:
    """Turn a row that may be missing into a dict or None."""
    return dict(row) if row else None


def load_claim(connection: sqlite3.Connection, claim_id: str) -> Claim:
    """Read a claim with its decision, sign-off and payment."""
    claim = find(
        connection,
        "SELECT status, record FROM claims WHERE claim_id = ?",
        claim_id,
        "claim",
    )
    decision = connection.execute(
        "SELECT outcome, payout, reason, policy_section, decided_at"
        " FROM decisions WHERE claim_id = ?",
        (claim_id,),
    ).fetchone()
    sign_off = connection.execute(SIGN_OFF, (claim_id,)).fetchone()
    payment = connection.execute(
        "SELECT amount, paid_at FROM payments WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    return Claim.model_validate(
        json.loads(claim["record"])
        | {
            "status": claim["status"],
            "decision": optional(decision),
            "sign_off": optional(sign_off),
            "payment": optional(payment),
        }
    )


@app.get("/api/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the backend is running."""
    return {"status": "ok"}


@app.get("/api/claims", operation_id="list_claims")
def list_claims() -> list[ClaimSummary]:
    """List the claims queue with where each claim stands."""
    with db.connect() as connection:
        rows = connection.execute(QUEUE).fetchall()
    return [
        ClaimSummary.model_validate(
            json.loads(row["record"])
            | {
                "customer_name": row["customer_name"],
                "status": row["status"],
                "outcome": row["outcome"],
                "payout": row["payout"],
                "paid": bool(row["paid"]),
            }
        )
        for row in rows
    ]


@app.get("/api/claims/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str) -> Claim:
    """Get one claim in full, with its decision, sign-off and payment."""
    with db.connect() as connection:
        return load_claim(connection, claim_id)


@app.get("/api/policies/{policy_id}", operation_id="get_policy")
def get_policy(policy_id: str) -> Policy:
    """Get a policy: its plan, add-ons, purchase date, trip and travelers."""
    with db.connect() as connection:
        row = find(
            connection,
            "SELECT record FROM policies WHERE policy_id = ?",
            policy_id,
            "policy",
        )
    return Policy.model_validate_json(row["record"])


@app.get("/api/customers/{customer_id}/history", operation_id="get_claim_history")
def get_claim_history(customer_id: str) -> ClaimHistory:
    """Get a customer's name, customer-since date and earlier claims."""
    with db.connect() as connection:
        row = find(
            connection,
            "SELECT record FROM customers WHERE customer_id = ?",
            customer_id,
            "customer",
        )
    return ClaimHistory.model_validate_json(row["record"])


@app.get("/api/handlers", operation_id="list_handlers")
def list_handlers() -> list[Handler]:
    """List the claims handlers."""
    with db.connect() as connection:
        rows = connection.execute(
            "SELECT record FROM handlers ORDER BY handler_id"
        ).fetchall()
    return [Handler.model_validate_json(row["record"]) for row in rows]


@app.post("/api/claims/{claim_id}/start", operation_id="start_claim")
def start_claim(claim_id: str) -> Claim:
    """Mark a claim in progress and clear the steps of an earlier, unfinished run."""
    with db.connect() as connection:
        status = status_of(connection, claim_id)
        if status not in {"waiting", "in_progress"}:
            refuse(f"Claim {claim_id} can't be started: it is {status}")
        connection.execute("DELETE FROM steps WHERE claim_id = ?", (claim_id,))
        set_status(connection, claim_id, "in_progress")
        return load_claim(connection, claim_id)


@app.post("/api/claims/{claim_id}/steps", operation_id="add_step")
def add_step(claim_id: str, step: NewStep) -> Step:
    """Record one step of the agent's work on a claim."""
    created_at = now()
    with db.connect() as connection:
        status_of(connection, claim_id)
        row = connection.execute(
            "INSERT INTO steps (claim_id, thread_id, kind, name, content, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?) RETURNING id",
            (claim_id, step.thread_id, step.kind, step.name, step.content, created_at),
        ).fetchone()
    return Step(id=row["id"], created_at=created_at, **step.model_dump())


@app.get("/api/claims/{claim_id}/steps", operation_id="list_steps")
def list_steps(claim_id: str) -> list[Step]:
    """List the agent's steps on a claim, in order."""
    with db.connect() as connection:
        status_of(connection, claim_id)
        rows = connection.execute(
            "SELECT id, thread_id, kind, name, content, created_at"
            " FROM steps WHERE claim_id = ? ORDER BY id",
            (claim_id,),
        ).fetchall()
    return [Step.model_validate(dict(row)) for row in rows]


@app.post("/api/claims/{claim_id}/decision", operation_id="record_decision")
def record_decision(claim_id: str, decision: Decision) -> Claim:
    """Record the decision on a claim in progress: approve, decline or refer."""
    with db.connect() as connection:
        status = status_of(connection, claim_id)
        if status != "in_progress":
            refuse(f"Claim {claim_id} isn't in progress, so it can't take a decision")
        connection.execute(
            "INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?)",
            (
                claim_id,
                decision.outcome,
                decision.payout,
                decision.reason,
                decision.policy_section,
                now(),
            ),
        )
        over_limit = decision.payout > approval_limit(connection)
        set_status(
            connection, claim_id, "waiting_for_sign_off" if over_limit else "decided"
        )
        return load_claim(connection, claim_id)


@app.post("/api/claims/{claim_id}/payment", operation_id="pay_claim")
def pay_claim(claim_id: str, payment: Payment) -> Claim:
    """Pay an approved claim the approved amount, if the payment rule allows it."""
    with db.connect() as connection:
        pay(connection, claim_id, payment.amount)
        return load_claim(connection, claim_id)


@app.post("/api/claims/{claim_id}/sign-off", operation_id="sign_off")
def sign_off(claim_id: str, request: SignOff) -> Claim:
    """Sign off a payout over the approval limit as a handler, which pays it."""
    with db.connect() as connection:
        status = status_of(connection, claim_id)
        sql = "SELECT record FROM handlers WHERE handler_id = ?"
        record = find(connection, sql, request.handler_id, "handler")["record"]
        handler = Handler.model_validate_json(record)
        if status != "waiting_for_sign_off":
            refuse(f"Claim {claim_id} isn't waiting for sign-off")
        if not handler.can_approve_over_limit:
            raise HTTPException(
                403, f"{handler.name} can't sign off payouts over the approval limit"
            )
        connection.execute(
            "INSERT INTO sign_offs VALUES (?, ?, ?)",
            (claim_id, handler.handler_id, now()),
        )
        sql = "SELECT payout FROM decisions WHERE claim_id = ?"
        pay(connection, claim_id, find(connection, sql, claim_id, "decision")["payout"])
        set_status(connection, claim_id, "decided")
        return load_claim(connection, claim_id)
