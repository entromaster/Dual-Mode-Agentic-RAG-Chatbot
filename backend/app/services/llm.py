"""
Wrapper around the google-genai SDK for Gemini LLM operations.

Provides: embedding, SQL generation, streaming text, and function-calling routing.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from google import genai
from google.genai import types

from app.config import GOOGLE_API_KEY, GEMINI_MODEL, EMBEDDING_MODEL, CURRENT_DATE

logger = logging.getLogger(__name__)

# ── Singleton client ──────────────────────────────────────────────────────────
_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY environment variable is not set.")
        _client = genai.Client(api_key=GOOGLE_API_KEY)
    return _client


# ── SQL Generation ────────────────────────────────────────────────────────────

_SQL_SYSTEM_PROMPT = f"""You are an expert SQL analyst. Today's date is {CURRENT_DATE}.
Given a natural-language question about an orders database, generate a single SQLite-compatible SELECT statement.

DATABASE SCHEMA:
  Table: orders
    order_id   TEXT     — e.g. "ORD-1001"
    customer   TEXT     — e.g. "Sneha Reddy", "Aarav Sharma", "Vikram Patel", "Priya Nair", "Tara Bose",
                           "Devansh Rao", "Nikhil Verma", "Sahil Khan", "Arjun Desai", "Pooja Agarwal",
                           "Meera Joshi", "Rohan Mehta", "Karan Singh", "Ananya Iyer", "Isha Gupta"
    product    TEXT     — one of: "Mechanical Keyboard", "USB-C Hub", "Laptop Stand", "Wireless Mouse",
                           "Noise-Cancelling Headphones", "Bluetooth Speaker", "Monitor Arm",
                           "Portable SSD 1TB", "Webcam 1080p", "Ergonomic Chair Cushion"
    amount     INTEGER  — price in INR (e.g. 4999)
    status     TEXT     — one of: "pending", "processing", "shipped", "delivered", "cancelled", "returned"
    order_date TEXT     — ISO format "YYYY-MM-DD" (range: 2025-12-17 to 2026-06-14)

RULES:
1. Return ONLY the raw SQL query — no markdown, no explanation, no backticks.
2. Use exact column and table names above.
3. String comparisons must be case-sensitive and match the exact values listed.
4. For date operations use SQLite date functions.
5. NEVER use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or any DDL/DML.
6. If a query cannot be answered from this schema, return: SELECT 'Query cannot be answered from available data' AS error;
"""


def generate_sql(question: str, schema_info: str = "") -> str:
    """Generate a SELECT statement from a natural-language question."""
    client = _get_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Content(role="user", parts=[types.Part(text=question)]),
        ],
        config=types.GenerateContentConfig(
            system_instruction=_SQL_SYSTEM_PROMPT,
            temperature=0.0,
            max_output_tokens=512,
        ),
    )
    sql = response.text.strip()
    # Strip stray markdown fences if the model adds them
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[-1]
    if sql.endswith("```"):
        sql = sql.rsplit("```", 1)[0]
    return sql.strip()


# ── Streaming text generation ─────────────────────────────────────────────────

async def stream_response(system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
    """Stream tokens from Gemini for the final answer."""
    client = _get_client()
    response = client.models.generate_content_stream(
        model=GEMINI_MODEL,
        contents=[
            types.Content(role="user", parts=[types.Part(text=user_prompt)]),
        ],
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.4,
            max_output_tokens=2048,
        ),
    )
    for chunk in response:
        if chunk.text:
            yield chunk.text


# ── Function-calling router ──────────────────────────────────────────────────

def route_query(
    message: str,
    history: list[types.Content],
    tools: list[types.Tool],
) -> types.GenerateContentResponse:
    """Send a message with tool declarations and return the raw response."""
    client = _get_client()

    contents = list(history)  # copy
    contents.append(types.Content(role="user", parts=[types.Part(text=message)]))

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=(
                f"You are a helpful assistant for Northwind Gadgets. Today's date is June 15, 2026.\n"
                f"You can answer questions about company policies using document search, "
                f"and questions about orders using the orders database.\n"
                f"Always cite your sources when answering from documents.\n"
                f"If you don't have information to answer a question, say so clearly. "
                f"Never make up policy details or data.\n"
                f"For SQL results, present the data in a clear, readable format."
            ),
            tools=tools,
            temperature=0.2,
            max_output_tokens=2048,
        ),
    )
    return response
