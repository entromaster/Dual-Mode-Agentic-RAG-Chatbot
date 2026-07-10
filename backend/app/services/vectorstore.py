"""
ChromaDB-backed vector store for RAG over PDF policy documents.

Ingests PDFs from the dataset directory, chunks by section headings,
embeds with Gemini, and supports semantic search.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

import chromadb
from PyPDF2 import PdfReader

from app.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME


logger = logging.getLogger(__name__)

# ── Chunking helper ──────────────────────────────────────────────────────────

_SECTION_RE = re.compile(r"(?=\n\d+\.\s)")  # split on numbered headings like "1. "


def _extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _chunk_text(text: str, source: str) -> list[dict]:
    """Split text on numbered section headings; fall back to single chunk."""
    sections = _SECTION_RE.split(text)
    chunks: list[dict] = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        # Try to extract section title (first line)
        first_line = section.split("\n", 1)[0].strip()
        section_title = first_line[:120] if first_line else "General"
        chunks.append(
            {
                "content": section,
                "source": source,
                "section": section_title,
            }
        )
    # If nothing was split, treat whole document as one chunk
    if not chunks and text.strip():
        chunks.append(
            {
                "content": text.strip(),
                "source": source,
                "section": "Full Document",
            }
        )
    return chunks


# ── VectorStore class ─────────────────────────────────────────────────────────


class VectorStore:
    """Manages a ChromaDB collection of embedded document chunks."""

    def __init__(self) -> None:
        self._chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        self._collection = self._chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    # ── Ingestion ─────────────────────────────────────────────────────────

    def ingest_documents(self, dataset_path: str) -> None:
        """Load all PDFs from *dataset_path*, chunk, embed, and store.

        Skips entirely if the collection already contains documents (idempotent).
        """
        if self._collection.count() > 0:
            logger.info(
                "VectorStore already contains %d documents — skipping ingestion.",
                self._collection.count(),
            )
            return

        dataset = Path(dataset_path)
        pdf_files = sorted(dataset.glob("*.pdf"))
        if not pdf_files:
            logger.warning("No PDF files found in %s", dataset)
            return

        all_chunks: list[dict] = []
        for pdf in pdf_files:
            logger.info("Extracting text from %s", pdf.name)
            text = _extract_pdf_text(pdf)
            chunks = _chunk_text(text, pdf.name)
            all_chunks.extend(chunks)

        logger.info("Total chunks: %d — embedding…", len(all_chunks))

        texts = [c["content"] for c in all_chunks]



        ids = [
            hashlib.md5(f"{c['source']}:{c['section']}:{idx}".encode()).hexdigest()
            for idx, c in enumerate(all_chunks)
        ]
        metadatas = [{"source": c["source"], "section": c["section"]} for c in all_chunks]

        self._collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
        )
        logger.info("Ingested %d chunks into ChromaDB.", len(all_chunks))

    # ── Search ────────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Semantic search — returns top-k results with scores."""
        results = self._collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        hits: list[dict] = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            hits.append(
                {
                    "content": doc,
                    "source": meta.get("source", ""),
                    "section": meta.get("section", ""),
                    "score": round(1 - dist, 4),  # cosine distance → similarity
                }
            )
        return hits
