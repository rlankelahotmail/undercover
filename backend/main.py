"""The UnderCover backend."""

import json
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from backend import db
from backend.models import Claim, ClaimHistory, ClaimSummary, Handler, Policy
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
