"""
SQL Tool — wraps Database + LLM to answer natural-language questions
about orders by generating, validating, and executing SQL.
"""

from __future__ import annotations

import logging

from app.services.database import Database
from app.services.llm import generate_sql

logger = logging.getLogger(__name__)


class SQLTool:
    """Natural-language → SQL → result tool for the orders database."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def query(self, question: str) -> dict:
        """Generate SQL from a question, execute it, and return results.

        Returns:
            {
                "sql_query": "SELECT ...",
                "columns": [...],
                "results": [[...], ...],
                "row_count": int,
                "error": str | None
            }
        """
        schema_info = self._db.get_schema()

        # 1. Generate SQL
        try:
            sql = generate_sql(question, schema_info)
            logger.info("Generated SQL: %s", sql)
        except Exception as exc:
            logger.error("SQL generation failed: %s", exc)
            return {
                "sql_query": "",
                "columns": [],
                "results": [],
                "row_count": 0,
                "error": f"Failed to generate SQL: {exc}",
            }

        # 2. Validate & execute
        try:
            result = self._db.execute_query(sql)
            return {
                "sql_query": sql,
                "columns": result["columns"],
                "results": result["rows"],
                "row_count": result["row_count"],
                "error": None,
            }
        except ValueError as exc:
            logger.warning("SQL validation failed: %s", exc)
            return {
                "sql_query": sql,
                "columns": [],
                "results": [],
                "row_count": 0,
                "error": f"SQL validation error: {exc}",
            }
        except Exception as exc:
            logger.error("SQL execution failed: %s", exc)
            return {
                "sql_query": sql,
                "columns": [],
                "results": [],
                "row_count": 0,
                "error": f"SQL execution error: {exc}",
            }
