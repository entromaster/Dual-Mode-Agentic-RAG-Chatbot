"""
SQLite database service for the orders data.

Loads orders.csv into an in-process SQLite database and exposes
a safe, read-only query interface.
"""

from __future__ import annotations

import csv
import logging
import sqlite3
from pathlib import Path

from app.config import SQLITE_DB_PATH, DATASET_DIR

logger = logging.getLogger(__name__)


class Database:
    """Manages an SQLite database backed by orders.csv."""

    def __init__(self) -> None:
        self._db_path = SQLITE_DB_PATH
        self._init_db()

    # ── Initialisation ────────────────────────────────────────────────────

    def _init_db(self) -> None:
        """Create the orders table and load CSV data (idempotent)."""
        csv_path = DATASET_DIR / "orders.csv"
        conn = sqlite3.connect(self._db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    order_id   TEXT PRIMARY KEY,
                    customer   TEXT NOT NULL,
                    product    TEXT NOT NULL,
                    amount     INTEGER NOT NULL,
                    status     TEXT NOT NULL,
                    order_date TEXT NOT NULL
                )
                """
            )
            # Check if data already loaded
            row_count = cur.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            if row_count > 0:
                logger.info("Orders table already has %d rows — skipping CSV import.", row_count)
                return

            if not csv_path.exists():
                logger.warning("orders.csv not found at %s", csv_path)
                return

            with open(csv_path, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                rows = [
                    (
                        row["order_id"],
                        row["customer"],
                        row["product"],
                        int(row["amount"]),
                        row["status"],
                        row["order_date"],
                    )
                    for row in reader
                ]
            cur.executemany(
                "INSERT OR IGNORE INTO orders (order_id, customer, product, amount, status, order_date) VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()
            logger.info("Loaded %d rows from orders.csv into SQLite.", len(rows))
        finally:
            conn.close()

    # ── Schema description for the LLM ────────────────────────────────────

    def get_schema(self) -> str:
        """Return a human-readable schema description for SQL generation prompts."""
        return (
            "Table: orders\n"
            "  order_id   TEXT     — unique order identifier (e.g. 'ORD-1001')\n"
            "  customer   TEXT     — customer full name\n"
            "  product    TEXT     — product name\n"
            "  amount     INTEGER  — price in INR\n"
            "  status     TEXT     — one of: pending, processing, shipped, delivered, cancelled, returned\n"
            "  order_date TEXT     — ISO date string (YYYY-MM-DD)\n"
        )

    # ── Query execution ──────────────────────────────────────────────────

    def execute_query(self, sql: str) -> dict:
        """Execute a read-only SELECT statement and return results.

        Returns:
            {columns: list[str], rows: list[list], row_count: int}

        Raises:
            ValueError  if the query is not a SELECT.
            sqlite3.Error on SQL execution problems.
        """
        normalised = sql.strip().rstrip(";").strip()
        # Safety: only allow SELECT statements
        if not normalised.upper().startswith("SELECT"):
            raise ValueError("Only SELECT statements are allowed.")

        # Reject dangerous keywords even within a SELECT (e.g. sub-queries with side-effects)
        _FORBIDDEN = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "ATTACH", "DETACH", "PRAGMA"}
        upper_sql = normalised.upper()
        for kw in _FORBIDDEN:
            if kw in upper_sql:
                raise ValueError(f"Forbidden keyword detected: {kw}")

        conn = sqlite3.connect(self._db_path)
        try:
            # Use read-only URI if possible (Python ≥ 3.12 flag, fallback gracefully)
            conn.execute("PRAGMA query_only = ON")
            cur = conn.cursor()
            cur.execute(normalised)
            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows = cur.fetchall()
            return {
                "columns": columns,
                "rows": [list(r) for r in rows],
                "row_count": len(rows),
            }
        finally:
            conn.close()
