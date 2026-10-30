"""Reset the database from UnderCover's records in data/: uv run -m backend.seed."""

import json
from pathlib import Path
from typing import Any

from backend import db

DATA = Path(__file__).parent.parent / "data"
INSTRUCTIONS = Path(__file__).parent / "instructions.md"


def load(name: str) -> Any:
    """Read one of the JSON files in data/."""
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def seed() -> str:
    """Recreate the database with every claim waiting, and say what it holds."""
    claims = load("claims.json")
    policies = load("policies.json")
    customers = load("customers.json")
    handlers = load("handlers.json")
    instructions = (
        INSTRUCTIONS.read_text(encoding="utf-8")
        + "\n"
        + (DATA / "policy_wording.md").read_text(encoding="utf-8")
    )
    with db.connect() as connection:
        connection.executescript(db.SCHEMA)
        connection.executemany(
            "INSERT INTO policies VALUES (?, ?)",
            [(policy["policy_id"], json.dumps(policy)) for policy in policies],
        )
        connection.executemany(
            "INSERT INTO customers VALUES (?, ?)",
            [(customer["customer_id"], json.dumps(customer)) for customer in customers],
        )
        connection.executemany(
            "INSERT INTO handlers VALUES (?, ?)",
            [(handler["handler_id"], json.dumps(handler)) for handler in handlers],
        )
        records = [
            {key: value for key, value in claim.items() if key != "status"}
            for claim in claims
        ]
        connection.executemany(
            "INSERT INTO claims VALUES (?, ?, ?, 'waiting', ?)",
            [
                (
                    record["claim_id"],
                    record["policy_id"],
                    record["customer_id"],
                    json.dumps(record),
                )
                for record in records
            ],
        )
        connection.execute(
            "INSERT INTO settings VALUES ('company', ?)",
            ((DATA / "company.json").read_text(encoding="utf-8"),),
        )
        connection.execute(
            "INSERT INTO settings VALUES ('instructions', ?)", (instructions,)
        )
    return (
        f"Seeded {len(claims)} claims, {len(policies)} policies, "
        f"{len(customers)} customers and {len(handlers)} handlers"
    )


if __name__ == "__main__":
    print(seed())
