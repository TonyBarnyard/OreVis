"""Persistent storage for the accounting ledger and client profile.

Everything lives in a single SQLite file so the agent is genuinely standalone —
no external database to run. The ledger follows standard double-entry rules:
every journal entry must have total debits equal to total credits.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

# Account types and their "normal" balance side. Assets and expenses increase
# with debits; liabilities, equity, and revenue increase with credits.
ACCOUNT_TYPES = {
    "asset": "debit",
    "liability": "credit",
    "equity": "credit",
    "revenue": "credit",
    "expense": "debit",
}

DEFAULT_DB = os.environ.get("FINANCE_DB", "finance_agent.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    code          TEXT UNIQUE NOT NULL,
    name          TEXT NOT NULL,
    type          TEXT NOT NULL CHECK (type IN ('asset','liability','equity','revenue','expense'))
);

CREATE TABLE IF NOT EXISTS journal_entries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    date          TEXT NOT NULL,          -- ISO 8601 (YYYY-MM-DD)
    memo          TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS journal_lines (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id      INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    account_id    INTEGER NOT NULL REFERENCES accounts(id),
    debit         REAL NOT NULL DEFAULT 0,
    credit        REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS profile (
    key           TEXT PRIMARY KEY,
    value         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lines_entry   ON journal_lines(entry_id);
CREATE INDEX IF NOT EXISTS idx_lines_account ON journal_lines(account_id);
"""


class Store:
    """Thin wrapper around a SQLite connection with the ledger schema applied."""

    def __init__(self, path: str = DEFAULT_DB):
        self.path = path
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    @contextmanager
    def cursor(self) -> Iterator[sqlite3.Cursor]:
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cur.close()

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        cur = self._conn.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows

    def query_one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        cur = self._conn.execute(sql, params)
        row = cur.fetchone()
        cur.close()
        return row

    def close(self) -> None:
        self._conn.close()
