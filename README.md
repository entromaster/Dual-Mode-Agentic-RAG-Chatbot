# 🤖 Dual-Mode Agentic RAG Chatbot

A production-grade AI chatbot for **Northwind Gadgets** that answers questions using two distinct retrieval strategies within a single conversational agent:

- **📄 Agentic RAG** — Vector retrieval over company policy documents with citations
- **🗃️ Text-to-SQL** — Natural language to SQL queries over structured order data
- **🔀 Hybrid** — Combines both sources for questions that span documents and data

> **Live Demo**: [Coming soon — deploy URL]

![Chatbot Demo](docs/demo.gif)

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        User (Browser)                         │
│                     Next.js Chat UI (:3000)                   │
└──────────────────┬───────────────────────────────────────────┘
                   │ POST /api/chat (SSE stream)
┌──────────────────▼───────────────────────────────────────────┐
│                    FastAPI Backend (:8000)                     │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Gemini Router (Function Calling)            │ │
│  │  Classifies query intent → picks tool(s) automatically  │ │
│  └────────┬──────────────────┬──────────────────┬──────────┘ │
│           │                  │                  │            │
│  ┌────────▼──────┐  ┌───────▼───────┐  ┌──────▼─────────┐  │
│  │ search_docs() │  │ query_orders()│  │   (no tools)   │  │
│  │   RAG Tool    │  │   SQL Tool    │  │  Out-of-scope  │  │
│  └───────┬───────┘  └───────┬───────┘  └──────┬─────────┘  │
│          │                  │                  │            │
│  ┌───────▼───────┐  ┌──────▼────────┐  ┌─────▼──────────┐ │
│  │   ChromaDB    │  │    SQLite     │  │  Safe fallback │ │
│  │ (5 PDF docs)  │  │ (201 orders)  │  │  "I don't know"│ │
│  └───────────────┘  └───────────────┘  └────────────────┘  │
│                              │                               │
│              Gemini 2.0 Flash (Streaming Response)           │
└──────────────────────────────────────────────────────────────┘
```

### Request Flow

1. User sends a question via the chat UI
2. FastAPI receives the request and passes it to the **Agent**
3. The Agent sends the question to **Gemini with function declarations** (tool definitions)
4. Gemini decides which tool(s) to call based on the question's intent
5. Tool results are fed back to Gemini for final answer generation
6. Response is **streamed token-by-token** via Server-Sent Events (SSE)
7. Frontend displays tokens incrementally along with tool metadata, citations, and SQL

---

## 🧠 Key Design Decisions

### LLM: Google Gemini 2.0 Flash

| Factor | Details |
|--------|---------|
| **Why** | Free tier, fast inference, excellent function calling, native streaming |
| **Routing** | Uses Gemini's native function calling — no fragile keyword rules |
| **SQL Gen** | Gemini generates SQL with schema + constraints in the prompt |
| **Streaming** | Token-level streaming via `generate_content_stream` |

### Embeddings: Gemini `text-embedding-004`

- 768-dimensional dense vectors
- Native integration with Gemini ecosystem
- Strong performance on retrieval benchmarks
- Free tier supports the small corpus easily

### Vector Store: ChromaDB (Persistent)

| Factor | Details |
|--------|---------|
| **Why** | Zero infrastructure, embedded, persistent across restarts |
| **Trade-off** | Not suitable for massive scale, but perfect for 5 docs |
| **Chunking** | Section-based splitting on numbered headings for policy docs |
| **Metadata** | Each chunk tagged with `{source, section}` for citations |

### Structured Database: SQLite

- Zero-setup, embeddable, deterministic
- Perfect for ~200 rows — no need for PostgreSQL overhead
- Read-only queries for safety (no DDL/DML)
- CSV loaded into a proper SQL table at startup

### Routing: Gemini Function Calling

The agent uses **Gemini's native function calling** rather than keyword matching or a separate classifier. Two tools are declared:

```
search_documents(query) → Search policy documents via vector RAG
query_orders(question)  → Query orders database via text-to-SQL
```

**How routing decisions work:**
- Gemini receives the user's message along with both tool declarations
- The LLM's understanding of the question determines which tool(s) to invoke
- For **document questions** (e.g., "What is the refund window?") → calls `search_documents`
- For **data questions** (e.g., "Total revenue last month?") → calls `query_orders`
- For **mixed questions** → calls both tools
- For **out-of-scope** → calls neither tool → system returns safe fallback

This approach is more robust than keyword matching because the LLM understands semantic intent and context.

---

## 📁 Project Structure

```
├── Dataset/                        # Provided dataset (untouched)
│   ├── hr_leave_policy.pdf
│   ├── pricing_discounts_policy.pdf
│   ├── product_faq.pdf
│   ├── returns_policy.pdf
│   ├── warranty_policy.pdf
│   └── orders.csv
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, CORS, SSE endpoint
│   │   ├── config.py               # Settings and constants
│   │   ├── agent.py                # Core agent: router + tool orchestration
│   │   ├── models.py               # Pydantic schemas
│   │   ├── services/
│   │   │   ├── llm.py              # Gemini client wrapper
│   │   │   ├── vectorstore.py      # ChromaDB + PDF ingestion
│   │   │   └── database.py         # SQLite + CSV loading
│   │   └── tools/
│   │       ├── rag_tool.py         # Vector RAG with citations
│   │       └── sql_tool.py         # Text-to-SQL + execution
│   └── requirements.txt
├── frontend/
│   └── src/app/
│       ├── page.tsx                # Main chat page
│       ├── globals.css             # Dark glassmorphism design system
│       ├── layout.tsx              # Root layout
│       └── components/
│           ├── ChatWindow.tsx      # Message list + auto-scroll
│           ├── MessageBubble.tsx   # Message + tool badge + citations + SQL
│           ├── InputBar.tsx        # Chat input
│           └── ToolBadge.tsx       # Tool indicator badges
├── Dockerfile                      # Multi-stage build
├── docker-compose.yml              # Local dev
├── .env.example                    # API key template
└── README.md                       # This file
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+**
- **Node.js 20+**
- **Google Gemini API Key** — get one free at [Google AI Studio](https://aistudio.google.com/apikey)

### Option 1: Local Development (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/dual-mode-rag-chatbot.git
cd dual-mode-rag-chatbot

# 2. Set up environment
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# 3. Start the backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 4. Start the frontend (in a new terminal)
cd frontend
npm install
npm run dev
```

The frontend will be at `http://localhost:3000` and the backend API at `http://localhost:8000`.

### Option 2: Docker

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# 2. Build and run
docker compose up --build

# The app will be available at http://localhost:8000
```

### Option 3: Docker (Manual Build)

```bash
docker build -t rag-chatbot .
docker run -e GOOGLE_API_KEY=your_key_here -p 8000:8000 rag-chatbot
```

---

## 💬 Example Queries

### Document Questions (RAG)
| Question | Expected Tool | Source |
|----------|--------------|--------|
| "What is the refund window?" | 📄 Document Search | returns_policy.pdf |
| "How many sick days do employees get?" | 📄 Document Search | hr_leave_policy.pdf |
| "What payment methods are accepted?" | 📄 Document Search | product_faq.pdf |
| "What does the warranty cover?" | 📄 Document Search | warranty_policy.pdf |
| "Is there a bulk discount?" | 📄 Document Search | pricing_discounts_policy.pdf |

### Data Questions (SQL)
| Question | Expected Tool | SQL Pattern |
|----------|--------------|-------------|
| "How many orders are pending?" | 🗃️ SQL Query | `SELECT COUNT(*) WHERE status='pending'` |
| "What was total revenue last month?" | 🗃️ SQL Query | `SELECT SUM(amount) WHERE order_date...` |
| "Show orders by Sneha Reddy" | 🗃️ SQL Query | `SELECT * WHERE customer='Sneha Reddy'` |
| "What's the most ordered product?" | 🗃️ SQL Query | `GROUP BY product ORDER BY COUNT(*)` |

### Mixed Questions
| Question | Expected Tools |
|----------|---------------|
| "Our return policy allows 30-day returns. Show me any orders returned after that window." | 📄 + 🗃️ Both |
| "What's the warranty period and how many returned orders are there?" | 📄 + 🗃️ Both |

### Out-of-Scope
| Question | Expected |
|----------|----------|
| "What's the weather today?" | ❌ Safe fallback |
| "Write me a poem" | ❌ Safe fallback |

---

## 🔧 Technical Details

### Streaming Protocol (SSE)

The `/api/chat` endpoint returns Server-Sent Events:

```
event: tool_used
data: {"tool": "document_search", "query": "refund window"}

event: citation
data: {"sources": [{"doc": "returns_policy.pdf", "section": "Return Window"}]}

event: token
data: {"content": "The refund"}

event: token  
data: {"content": " window is 30 days."}

event: done
data: {}
```

### Safety Guardrails

- **SQL**: Only `SELECT` statements allowed; read-only SQLite connection
- **RAG**: Citations always included; model instructed to never invent policy text
- **Out-of-scope**: Questions without tool calls receive a safe "I don't have that information" response
- **No hallucination**: System prompt explicitly forbids fabricating data or policy details

### Current Date

As specified in the assignment, the system treats **June 15, 2026** as the current date for all time-based queries.

---

## ⚠️ Known Limitations

1. **No conversation memory persistence**: Chat history is maintained in the frontend session only. Refreshing the page clears the conversation.
2. **Single-user**: No authentication or multi-user session management.
3. **Small corpus**: The vector store is optimized for 5 documents. For a larger corpus, consider pgvector or Pinecone.
4. **SQL generation**: Complex multi-table queries are not needed (single table), but very ambiguous natural language may produce imperfect SQL.
5. **No retry logic**: If the Gemini API is temporarily unavailable, the request fails without retry.
6. **Static date**: The "current date" is hardcoded to June 15, 2026 as required by the assignment.
7. **Embedding re-computation**: On first startup, all documents are embedded and stored. Subsequent startups skip ingestion if the collection exists.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
