# Polymath - agents.md

## Project Overview
Polymath is a multi-source RAG research assistant with a C++ text chunker, Python RAG pipeline, and MCP server interface. It ingests PDFs, Markdown, and code files into a local vector store and answers questions with source attribution.

## Architecture
- **C++ Chunker**: SemanticChunker class, compiled via CMake + pybind11, imported as `fast_chunker`
- **Ingestion**: Parsers (PDF/MD/code) → C++ chunker → sentence-transformers embeddings → ChromaDB
- **RAG Pipeline**: ChromaDB retrieval → prompt construction → Ollama generation
- **REST API**: FastAPI on port 8000 (`/query`, `/ingest`, `/sources`)
- **MCP Server**: TypeScript on stdio, calls REST API, exposes 3 tools
- **Frontend**: Vanilla JS chat interface

## Tech Constraints
- All free/local: no paid APIs, no cloud services
- LLM via Ollama (Mistral or Llama 3) on localhost:11434
- Embeddings via sentence-transformers (all-MiniLM-L6-v2), runs on CPU
- ChromaDB as embedded persistent database
- C++ compiled with CMake, requires pybind11 and a C++17 compiler

## Code Conventions
- Python: type hints, docstrings, pytest for testing
- C++: modern C++17, const correctness, RAII patterns
- TypeScript: strict mode, async/await for HTTP calls
- API schemas defined with Pydantic models
- Environment variables for all configurable values

## File Structure
```
chunker/     - C++ source, pybind11 bindings, CMakeLists.txt
ingestion/   - parsers, embedder, store
rag/         - retriever, generator, pipeline orchestrator
api/         - FastAPI app and Pydantic schemas
mcp-server/  - TypeScript MCP server (src/index.ts, src/tools.ts)
frontend/    - HTML/CSS/JS chat UI
tests/       - Python pytest tests
```

## Key Decisions
- C++ chunker over Python for 10x performance on large documents
- ChromaDB over FAISS because it handles metadata filtering and persistence natively
- MCP over custom tool protocol for interoperability with any MCP client
- pybind11 over ctypes for type-safe, Pythonic C++ bindings
- sentence-transformers over OpenAI embeddings for zero-cost local operation
