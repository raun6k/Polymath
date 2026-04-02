"""FastAPI application for Polymath RAG research assistant."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .schemas import (
    QueryRequest,
    QueryResponse,
    SourceInfo,
    IngestResponse,
    SourcesResponse,
    SourceDetail,
    HealthResponse,
)

# Ensure project root is on sys.path so sibling packages resolve
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag.pipeline import run_query
from ingestion.orchestrator import ingest_document, _USE_CPP
from ingestion.store import list_sources

app = FastAPI(
    title="Polymath",
    description="Multi-Source RAG Research Assistant",
    version="1.0.0",
)

# Allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the frontend at /
_frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
if _frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        chunker="cpp" if _USE_CPP else "python_fallback",
    )


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """
    Ask a question and get an answer synthesized from the knowledge base.

    Returns the answer text plus source attribution for each cited document.
    """
    try:
        result = run_query(
            question=request.question,
            top_k=request.top_k,
            model=request.model,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return QueryResponse(
        answer=result["answer"],
        sources=[SourceInfo(**s) for s in result["sources"]],
        chunks_used=result["chunks_used"],
    )


@app.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...)) -> IngestResponse:
    """
    Upload and ingest a document (PDF, Markdown, or code file) into the knowledge base.
    """
    suffix = Path(file.filename or "upload").suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = ingest_document(tmp_path, source_name=file.filename or None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return IngestResponse(
        source=result["source"],
        doc_type=result["doc_type"],
        chunks_stored=result["chunks_stored"],
        chunker_used=result["chunker_used"],
        message=f"Successfully ingested {result['chunks_stored']} chunks from '{result['source']}'.",
    )


@app.post("/ingest/path", response_model=IngestResponse)
async def ingest_by_path(path: str = Form(...)) -> IngestResponse:
    """Ingest a document by server-side file path (for MCP server use)."""
    if not Path(path).exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    try:
        result = ingest_document(path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return IngestResponse(
        source=result["source"],
        doc_type=result["doc_type"],
        chunks_stored=result["chunks_stored"],
        chunker_used=result["chunker_used"],
        message=f"Successfully ingested {result['chunks_stored']} chunks from '{result['source']}'.",
    )


@app.get("/sources", response_model=SourcesResponse)
async def sources() -> SourcesResponse:
    """List all ingested documents with their chunk counts."""
    try:
        raw = list_sources()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    details = [SourceDetail(**s) for s in raw]
    return SourcesResponse(
        sources=details,
        total_documents=len(details),
        total_chunks=sum(d.chunk_count for d in details),
    )
