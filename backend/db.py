"""The UnderCover database, in SQLite."""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DEFAULT_PATH = Path(__file__).parent / "undercover.db"

SCHEMA = """
DROP TABLE IF EXISTS steps;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS sign_offs;
DROP TABLE IF EXISTS decisions;
DROP TABLE IF EXISTS claims;
DROP TABLE IF EXISTS policies;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS handlers;
DROP TABLE IF EXISTS settings;

CREATE TABLE policies (policy_id TEXT PRIMARY KEY, record TEXT NOT NULL);
CREATE TABLE customers (customer_id TEXT PRIMARY KEY, record TEXT NOT NULL);
CREATE TABLE handlers (handler_id TEXT PRIMARY KEY, record TEXT NOT NULL);
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE claims (
    claim_id TEXT PRIMARY KEY,
    policy_id TEXT NOT NULL REFERENCES policies,
    customer_id TEXT NOT NULL REFERENCES customers,
    status TEXT NOT NULL,
    record TEXT NOT NULL
);
CREATE TABLE decisions (
    claim_id TEXT PRIMARY KEY REFERENCES claims,
    outcome TEXT NOT NULL,
    payout REAL NOT NULL,
    reason TEXT NOT NULL,
    policy_section TEXT NOT NULL,
    decided_at TEXT NOT NULL
);
CREATE TABLE sign_offs (
    claim_id TEXT PRIMARY KEY REFERENCES claims,
    handler_id TEXT NOT NULL REFERENCES handlers,
    signed_off_at TEXT NOT NULL
);
CREATE TABLE payments (
    claim_id TEXT PRIMARY KEY REFERENCES claims,
    amount REAL NOT NULL,
    paid_at TEXT NOT NULL
);
CREATE TABLE steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT NOT NULL REFERENCES claims,
    thread_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def path() -> Path:
    """Return the database's path: UNDERCOVER_DB if set, or backend/undercover.db."""
    return Path(os.getenv("UNDERCOVER_DB", DEFAULT_PATH))


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Open the database for one unit of work, committed if it succeeds."""
    connection = sqlite3.connect(path())
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()
