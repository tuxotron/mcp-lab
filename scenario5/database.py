import os
import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(__file__).with_name("expense_reports.db")


def database_path() -> Path:
    return Path(os.getenv("REPORTS_DB_PATH", DEFAULT_DB_PATH))


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    connection = sqlite3.connect(path or database_path())
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(path: Path | str | None = None) -> None:
    """Create a small deterministic dataset without overwriting existing rows."""
    with connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS expense_reports (
                id INTEGER PRIMARY KEY,
                owner_id INTEGER NOT NULL REFERENCES users(id),
                submitted_on TEXT NOT NULL,
                merchant TEXT NOT NULL,
                amount_cents INTEGER NOT NULL,
                card_last_four TEXT NOT NULL,
                purpose TEXT NOT NULL
            );
            """
        )
        connection.executemany(
            "INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)",
            [(1, "alice"), (2, "bob")],
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO expense_reports
                (id, owner_id, submitted_on, merchant, amount_cents, card_last_four, purpose)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (101, 1, "2026-09-03", "Northwind Rail", 18900, "1042", "Customer workshop travel"),
                (102, 1, "2026-09-04", "Harbor Hotel", 42850, "1042", "Customer workshop lodging"),
                (201, 2, "2026-09-10", "Acme Legal", 275000, "7781", "Confidential acquisition review"),
                (202, 2, "2026-09-12", "Cloud Nine", 6499, "7781", "Project Atlas test environment"),
            ],
        )


def _serialize(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [
        {
            "report_id": row["id"],
            "owner": row["username"],
            "submitted_on": row["submitted_on"],
            "merchant": row["merchant"],
            "amount": f"{row['amount_cents'] / 100:.2f}",
            "card_last_four": row["card_last_four"],
            "purpose": row["purpose"],
        }
        for row in rows
    ]


def get_all_reports(path: Path | str | None = None) -> list[dict[str, Any]]:
    """Intentionally unsafe: return every tenant's records."""
    initialize_database(path)
    with connect(path) as connection:
        rows = connection.execute(
            """
            SELECT reports.*, users.username
            FROM expense_reports AS reports
            JOIN users ON users.id = reports.owner_id
            ORDER BY reports.id
            """
        ).fetchall()
    return _serialize(rows)


def get_reports_for_username(
    username: str, path: Path | str | None = None
) -> list[dict[str, Any]]:
    """Enforce row ownership in SQL using server-derived identity."""
    initialize_database(path)
    with connect(path) as connection:
        rows = connection.execute(
            """
            SELECT reports.*, users.username
            FROM expense_reports AS reports
            JOIN users ON users.id = reports.owner_id
            WHERE reports.owner_id = (
                SELECT id FROM users WHERE username = ?
            )
            ORDER BY reports.id
            """,
            (username,),
        ).fetchall()
    return _serialize(rows)
