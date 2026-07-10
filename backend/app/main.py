"""
FastAPI application entry point.

- Initialises VectorStore, Database, and Agent on startup
- Exposes POST /api/chat (SSE streaming) and GET /api/health
- Serves static frontend files if present
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import DATASET_DIR
from app.models import ChatRequest
from app.services.vectorstore import VectorStore
from app.services.database import Database
from app.tools.rag_tool import RAGTool
from app.tools.sql_tool import SQLTool
from app.agent import Agent

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Northwind Gadgets Agentic RAG Chatbot",
    version="1.0.0",
    description="Dual-mode chatbot: RAG over policy documents + SQL over orders data.",
)

# CORS — allow all origins during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global singletons (set during startup) ────────────────────────────────────
_agent: Agent | None = None


@app.on_event("startup")
async def startup() -> None:
    global _agent
    logger.info("🚀  Starting up…")

    # 1. Vector store + document ingestion
    logger.info("Initialising VectorStore (dataset: %s)", DATASET_DIR)
    vs = VectorStore()
    vs.ingest_documents(str(DATASET_DIR))

    # 2. Database
    logger.info("Initialising Database…")
    db = Database()

    # 3. Tools
    rag_tool = RAGTool(vs)
    sql_tool = SQLTool(db)

    # 4. Agent
    _agent = Agent(rag_tool, sql_tool)
    logger.info("✅  Startup complete.")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health() -> dict:
    return {"status": "healthy", "service": "Northwind Gadgets Chatbot API"}


@app.post("/api/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Stream an agent response as Server-Sent Events."""
    if _agent is None:
        return JSONResponse(
            status_code=503,
            content={"error": "Service not ready — still initialising."},
        )

    history = [{"role": m.role, "content": m.content} for m in request.history]

    async def event_generator():
        async for event in _agent.process_message(request.message, history, request.api_key):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering if behind proxy
        },
    )


# ── Static file serving (for production — optional) ──────────────────────────
from app.config import STATIC_DIR as _STATIC_DIR_SETTING  # noqa: E402

_static_dir = Path(_STATIC_DIR_SETTING)
if _static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
    logger.info("Serving static files from %s", _static_dir)

