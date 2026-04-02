"""Ingestion orchestrator: parse → chunk → embed → store."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from .parsers import parse_document
from .embedder import embed_texts
from .store import store_chunks

# Try to import the C++ fast_chunker; fall back to pure Python if not built yet
try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from fast_chunker import SemanticChunker as _CppChunker  # type: ignore

    _USE_CPP = True
except ImportError:
    _USE_CPP = False

MAX_TOKENS = int(os.environ.get("CHUNK_MAX_TOKENS", "256"))
OVERLAP_TOKENS = int(os.environ.get("CHUNK_OVERLAP_TOKENS", "32"))


def _python_chunk(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    """Pure-Python fallback chunker (sentence-boundary aware)."""
    import re

    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])|(?<=\n)\n", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks: list[str] = []
    current_sents: list[str] = []
    current_tokens = 0

    def _est(s: str) -> int:
        return len(s.split())

    for sent in sentences:
        est = _est(sent)
        if current_tokens + est > max_tokens and current_sents:
            chunks.append(" ".join(current_sents))
            # Keep overlap sentences
            overlap_sents: list[str] = []
            overlap_t = 0
            for s in reversed(current_sents):
                if overlap_t + _est(s) > overlap_tokens:
                    break
                overlap_sents.insert(0, s)
                overlap_t += _est(s)
            current_sents = overlap_sents
            current_tokens = overlap_t

        current_sents.append(sent)
        current_tokens += est

    if current_sents:
        chunks.append(" ".join(current_sents))

    return chunks


def ingest_document(
    path: str,
    extra_metadata: dict[str, Any] | None = None,
    max_tokens: int = MAX_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> dict[str, Any]:
    """
    Parse, chunk, embed, and store a document.

    Parameters
    ----------
    path : str
        Path to the document file.
    extra_metadata : dict | None
        Additional metadata to attach to each chunk.
    max_tokens : int
        Maximum tokens per chunk (default from env CHUNK_MAX_TOKENS).
    overlap_tokens : int
        Overlap tokens between consecutive chunks.

    Returns
    -------
    dict
        Summary: {'source', 'doc_type', 'chunks_stored', 'chunker_used'}.
    """
    # 1. Parse
    text, doc_type = parse_document(path)
    source = Path(path).name

    # 2. Chunk
    if _USE_CPP:
        chunker = _CppChunker(max_tokens, overlap_tokens)
        raw_chunks = chunker.chunk(text)
        chunk_texts = [c.text for c in raw_chunks]
        chunker_used = "cpp"
    else:
        chunk_texts = _python_chunk(text, max_tokens, overlap_tokens)
        chunker_used = "python_fallback"

    if not chunk_texts:
        return {
            "source": source,
            "doc_type": doc_type,
            "chunks_stored": 0,
            "chunker_used": chunker_used,
        }

    # 3. Embed
    embeddings = embed_texts(chunk_texts)

    # 4. Store
    n_stored = store_chunks(
        chunk_texts,
        embeddings,
        source=source,
        doc_type=doc_type,
        extra_metadata=extra_metadata,
    )

    return {
        "source": source,
        "doc_type": doc_type,
        "chunks_stored": n_stored,
        "chunker_used": chunker_used,
    }
