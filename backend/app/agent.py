"""
Core agentic orchestrator.

Uses Gemini function-calling to route user queries to the right tool
(document search or orders DB), executes the tool, then streams a
final answer back as Server-Sent Events.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from google.genai import types

from app.config import CURRENT_DATE
from app.services.llm import route_query, stream_response
from app.tools.rag_tool import RAGTool
from app.tools.sql_tool import SQLTool

logger = logging.getLogger(__name__)

# ── Tool declarations for Gemini function calling ────────────────────────────

_TOOL_DECLARATIONS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="search_documents",
            description=(
                "Search Northwind Gadgets company policy documents including "
                "HR leave policy, pricing & discounts, product FAQ, returns policy, "
                "and warranty policy. Use this for any question about company policies, "
                "rules, procedures, leave, returns, warranty, pricing, delivery, or payments."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(
                        type=types.Type.STRING,
                        description="The search query to find relevant policy documents.",
                    ),
                },
                required=["query"],
            ),
        ),
        types.FunctionDeclaration(
            name="query_orders",
            description=(
                "Query the Northwind Gadgets orders database. Use this for questions "
                "about specific orders, order statuses, customer purchase history, "
                "revenue, product sales, order counts, or any data question about orders. "
                "The database contains order_id, customer, product, amount, status, and order_date."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "question": types.Schema(
                        type=types.Type.STRING,
                        description="The natural-language question about orders data.",
                    ),
                },
                required=["question"],
            ),
        ),
    ]
)

_SYSTEM_PROMPT = (
    f"You are a helpful assistant for Northwind Gadgets. Today's date is June 15, 2026.\n"
    f"You can answer questions about company policies using document search, "
    f"and questions about orders using the orders database.\n"
    f"Always cite your sources when answering from documents.\n"
    f"If you don't have information to answer a question, say so clearly. "
    f"Never make up policy details or data.\n"
    f"For SQL results, present the data in a clear, readable format."
)


def _build_history(history: list[dict]) -> list[types.Content]:
    """Convert the chat history to google.genai Content objects."""
    contents: list[types.Content] = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part(text=msg["content"])])
        )
    return contents


def _sse(event: str, data: dict) -> str:
    """Format a single SSE frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ── Main agent entry point ───────────────────────────────────────────────────


class Agent:
    """Agentic orchestrator that routes queries via Gemini function calling."""

    def __init__(self, rag_tool: RAGTool, sql_tool: SQLTool) -> None:
        self._rag = rag_tool
        self._sql = sql_tool

    async def process_message(
        self, message: str, history: list[dict], api_key: str | None = None
    ) -> AsyncIterator[str]:
        """Process a user message and yield SSE event strings."""

        try:
            # 1. Build conversation history
            hist_contents = _build_history(history)

            # 2. Ask Gemini which tool(s) to call
            response = route_query(message, hist_contents, [_TOOL_DECLARATIONS], api_key)

            # 3. Check for function calls in the response
            function_calls: list = []
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        function_calls.append(part.function_call)

            # No tool calls → the model wants to answer directly or it's out-of-scope
            if not function_calls:
                text = response.text or ""
                if text:
                    # Model answered directly (possibly out-of-scope deflection)
                    yield _sse("token", {"content": text})
                    yield _sse("done", {})
                else:
                    yield _sse("token", {"content": "I can only help with Northwind Gadgets company policies and order information. Could you rephrase your question?"})
                    yield _sse("done", {})
                return

            # 4. Execute each function call
            tool_results: list[dict] = []
            function_response_parts: list[types.Part] = []

            for fc in function_calls:
                fn_name = fc.name
                fn_args = dict(fc.args) if fc.args else {}

                logger.info("Agent calling tool: %s(%s)", fn_name, fn_args)

                if fn_name == "search_documents":
                    query = fn_args.get("query", message)
                    yield _sse("tool_used", {"tool": "document_search"})

                    result = self._rag.search(query)
                    tool_results.append({"tool": "document_search", "result": result})

                    # Emit citation event
                    yield _sse("citation", {"sources": result["sources"]})

                    # Build context for final answer
                    context_parts = []
                    for r in result["results"]:
                        context_parts.append(
                            f"[Source: {r['source']} — {r['section']}]\n{r['content']}"
                        )
                    context_text = "\n\n---\n\n".join(context_parts)

                    function_response_parts.append(
                        types.Part.from_function_response(
                            name="search_documents",
                            response={"result": context_text},
                        )
                    )

                elif fn_name == "query_orders":
                    question = fn_args.get("question", message)
                    yield _sse("tool_used", {"tool": "orders_database"})

                    result = self._sql.query(question)
                    tool_results.append({"tool": "orders_database", "result": result})

                    # Emit SQL query event
                    yield _sse("sql_query", {"query": result["sql_query"]})

                    # Build result text for final answer
                    if result.get("error"):
                        result_text = f"Error: {result['error']}"
                    else:
                        result_text = (
                            f"SQL Query: {result['sql_query']}\n"
                            f"Columns: {result['columns']}\n"
                            f"Results ({result['row_count']} rows): {json.dumps(result['results'][:50])}"
                        )

                    function_response_parts.append(
                        types.Part.from_function_response(
                            name="query_orders",
                            response={"result": result_text},
                        )
                    )

                else:
                    logger.warning("Unknown function call: %s", fn_name)

            # 5. Send tool results back to Gemini for final streamed answer
            # Build the full conversation for the follow-up call
            followup_contents = list(hist_contents)
            followup_contents.append(
                types.Content(role="user", parts=[types.Part(text=message)])
            )
            # Model's function-call turn
            followup_contents.append(response.candidates[0].content)
            # Tool result turn
            followup_contents.append(
                types.Content(role="user", parts=function_response_parts)
            )

            # Build a user prompt from the tool results for the streaming call
            tool_context_parts: list[str] = []
            for tr in tool_results:
                if tr["tool"] == "document_search":
                    tool_context_parts.append(
                        "DOCUMENT SEARCH RESULTS:\n" +
                        "\n---\n".join(
                            f"[{r['source']} — {r['section']}]\n{r['content']}"
                            for r in tr["result"]["results"]
                        )
                    )
                elif tr["tool"] == "orders_database":
                    r = tr["result"]
                    if r.get("error"):
                        tool_context_parts.append(f"DATABASE ERROR: {r['error']}")
                    else:
                        tool_context_parts.append(
                            f"DATABASE RESULTS:\n"
                            f"SQL: {r['sql_query']}\n"
                            f"Columns: {', '.join(r['columns'])}\n"
                            f"Rows ({r['row_count']} total):\n" +
                            "\n".join(str(row) for row in r["results"][:50])
                        )

            user_prompt = (
                f"User question: {message}\n\n"
                + "\n\n".join(tool_context_parts)
                + "\n\nProvide a clear, helpful answer based on the above information. "
                "Cite document sources when using policy information. "
                "Format data results in a readable way."
            )

            async for token in stream_response(_SYSTEM_PROMPT, user_prompt, api_key):
                yield _sse("token", {"content": token})

            yield _sse("done", {})

        except Exception as exc:
            logger.exception("Agent error: %s", exc)
            yield _sse("error", {"message": str(exc)})
