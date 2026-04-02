"""Pydantic request/response schemas for the Polymath API."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Query ─────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural-language question")
    top_k: int = Field(5, ge=1, le=20, description="Number of chunks to retrieve")
    model: str | None = Field(None, description="Ollama model override")


class SourceInfo(BaseModel):
    source: str
    doc_type: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]
    chunks_used: int


# ── Ingest ────────────────────────────────────────────────────────────────────

class IngestResponse(BaseModel):
    source: str
    doc_type: str
    chunks_stored: int
    chunker_used: str
    message: str


# ── Sources list ──────────────────────────────────────────────────────────────

class SourceDetail(BaseModel):
    source: str
    doc_type: str
    chunk_count: int


class SourcesResponse(BaseModel):
    sources: list[SourceDetail]
    total_documents: int
    total_chunks: int


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    chunker: str
    version: str = "1.0.0"
