# Polymath

Multi-Source RAG Research Assistant with MCP Server

Polymath ingests PDFs, Markdown, and code files into a local vector store and answers questions that synthesize information across sources. It features a high-performance C++ text chunker (via pybind11), a RAG pipeline backed by Ollama, a FastAPI REST interface, an MCP-compliant TypeScript server, and a vanilla JS chat UI.

---

## Architecture

```
Documents (PDF/MD/Code)
        │
        ▼
   Parsers (PyMuPDF / plain text / code)
        │
        ▼
C++ SemanticChunker (pybind11)   ←── 10x faster than pure Python
        │
        ▼
sentence-transformers (all-MiniLM-L6-v2, local CPU)
        │
        ▼
    ChromaDB  (./vectorstore, embedded, persistent)
        │
   ┌────┴──────────────────────────┐
   ▼                               ▼
FastAPI :8000               MCP Server (stdio)
   │                               │
   ▼                               ▼
Web Chat UI              Claude / any MCP client
```

**Query flow:** User question → embed → ChromaDB vector search → top-K chunks → prompt builder → Ollama → answer + sources

---

## Tech Stack

| Component     | Technology                          |
|---------------|-------------------------------------|
| Text chunking | C++17 + pybind11                    |
| Build system  | CMake                               |
| Embeddings    | sentence-transformers all-MiniLM-L6-v2 |
| Vector store  | ChromaDB (embedded, persistent)     |
| LLM           | Ollama (Mistral / Llama 3)          |
| REST API      | FastAPI                             |
| MCP server    | Node.js / TypeScript                |
| PDF parsing   | PyMuPDF (fitz)                      |
| Frontend      | Vanilla JS + HTML/CSS               |
| Testing       | pytest + Google Test                |

All free and local — no paid APIs, no cloud services.

---

## Prerequisites

| Tool       | Version   | Install                                      |
|------------|-----------|----------------------------------------------|
| Python     | ≥ 3.10    | [python.org](https://www.python.org)         |
| CMake      | ≥ 3.15    | `brew install cmake` / `apt install cmake`   |
| C++17 compiler | any   | Xcode CLT / `build-essential`               |
| Node.js    | ≥ 18      | [nodejs.org](https://nodejs.org)             |
| Ollama     | latest    | [ollama.com](https://ollama.com)             |

---

## Setup

### 1. Clone & install Python dependencies

```bash
git clone <repo-url> polymath && cd polymath
pip install -r requirements.txt
```

### 2. Build the C++ chunker

```bash
cmake -S chunker -B chunker/build -DCMAKE_BUILD_TYPE=Release
cmake --build chunker/build --parallel
cmake --install chunker/build --prefix .
```

This produces `fast_chunker*.so` (macOS: `.dylib`, Windows: `.pyd`) in the project root. Python will auto-import it.

### 3. Install MCP server dependencies

```bash
cd mcp-server
npm install
npm run build
cd ..
```

### 4. Pull an Ollama model

```bash
ollama pull mistral
# or: ollama pull llama3
```

---

## Running

### Start the REST API

```bash
uvicorn api.main:app --reload --port 8000
```

Open [http://localhost:8000/app](http://localhost:8000/app) for the chat UI, or [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive API docs.

### Start the MCP server (optional — for Claude / Cursor integration)

```bash
node mcp-server/dist/index.js
```

Configure it in your MCP client as a stdio server pointing to `node mcp-server/dist/index.js`.

---

## API Reference

| Method | Endpoint       | Description                          |
|--------|----------------|--------------------------------------|
| POST   | `/query`        | Ask a question, returns answer + sources |
| POST   | `/ingest`       | Upload & ingest a document           |
| GET    | `/sources`      | List all ingested documents          |
| GET    | `/health`       | Health check                         |

**Example — ingest a PDF:**
```bash
curl -X POST http://localhost:8000/ingest \
  -F "file=@paper.pdf"
```

**Example — query:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the main findings?", "top_k": 5}'
```

---

## MCP Tools

The MCP server exposes three tools to any compatible AI client:

| Tool                   | Description                                     |
|------------------------|-------------------------------------------------|
| `search_knowledge_base`| Ask a question; returns answer + source citations |
| `ingest_document`      | Ingest a file by server-side path               |
| `list_sources`         | List all ingested documents                     |

**Claude Desktop config** (`~/.config/claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "polymath": {
      "command": "node",
      "args": ["/absolute/path/to/polymath/mcp-server/dist/index.js"]
    }
  }
}
```

---

## Configuration

All values configurable via environment variables:

| Variable             | Default                | Description                      |
|----------------------|------------------------|----------------------------------|
| `OLLAMA_BASE_URL`    | `http://localhost:11434` | Ollama server URL              |
| `OLLAMA_MODEL`       | `mistral`              | Model name                       |
| `OLLAMA_TIMEOUT`     | `120`                  | Request timeout (seconds)        |
| `EMBED_MODEL`        | `all-MiniLM-L6-v2`     | Sentence-transformers model      |
| `VECTORSTORE_PATH`   | `./vectorstore`        | ChromaDB persistence directory   |
| `CHROMA_COLLECTION`  | `polymath`             | Collection name                  |
| `CHUNK_MAX_TOKENS`   | `256`                  | Max tokens per chunk             |
| `CHUNK_OVERLAP_TOKENS` | `32`               | Overlap tokens between chunks    |
| `RETRIEVER_TOP_K`    | `5`                    | Chunks retrieved per query       |
| `POLYMATH_API_URL`   | `http://localhost:8000` | API URL for MCP server          |

---

## Testing

### Python tests
```bash
pytest tests/ -v
```

### C++ tests
```bash
ctest --test-dir chunker/build --output-on-failure
```

### Benchmark (C++ vs Python chunker)
```bash
python tests/benchmark_chunker.py --words 10000
```

---

## Supported File Types

| Extension | Type     |
|-----------|----------|
| `.pdf`    | PDF      |
| `.md`, `.markdown`, `.txt` | Markdown/text |
| `.py`, `.ts`, `.js`, `.cpp`, `.c`, `.h`, `.hpp`, `.java`, `.go`, `.rs` | Code |

---

## File Structure

```
polymath/
├── chunker/
│   ├── src/
│   │   ├── chunker.hpp        # SemanticChunker class declaration
│   │   ├── chunker.cpp        # Implementation
│   │   └── bindings.cpp       # pybind11 Python bindings
│   ├── tests/
│   │   └── test_chunker.cpp   # Google Test suite
│   └── CMakeLists.txt
├── ingestion/
│   ├── parsers.py             # PDF / Markdown / code parsers
│   ├── embedder.py            # sentence-transformers wrapper
│   ├── store.py               # ChromaDB interface
│   └── orchestrator.py        # parse → chunk → embed → store
├── rag/
│   ├── retriever.py           # Vector similarity search
│   ├── generator.py           # Ollama prompt + generation
│   └── pipeline.py            # Orchestrate retrieve → generate
├── api/
│   ├── main.py                # FastAPI app
│   └── schemas.py             # Pydantic models
├── mcp-server/
│   ├── src/
│   │   ├── index.ts           # MCP server entry point
│   │   └── tools.ts           # Tool implementations
│   ├── package.json
│   └── tsconfig.json
├── frontend/
│   ├── index.html             # Chat UI
│   ├── style.css
│   └── app.js
├── tests/
│   ├── test_ingestion.py
│   ├── test_rag.py
│   ├── test_api.py
│   └── benchmark_chunker.py
├── .github/workflows/ci.yml
├── agents.md
├── requirements.txt
└── README.md
```
