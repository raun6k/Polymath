"""Orchestrates retrieve → generate and returns answer + sources."""

from __future__ import annotations

import os
from typing import Any

from .retriever import retrieve
from .generator import generate

TOP_K = int(os.environ.get("RETRIEVER_TOP_K", "5"))


def run_query(
    question: str,
    top_k: int = TOP_K,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Run a full RAG query: retrieve relevant chunks then generate an answer.

    Parameters
    ----------
    question : str
        The user's natural-language question.
    top_k : int
        Number of chunks to retrieve.
    model : str | None
        Ollama model override. Defaults to env OLLAMA_MODEL.

    Returns
    -------
    dict
        {
          'answer': str,
          'sources': list[{'source', 'doc_type', 'score'}],
          'chunks_used': int,
        }
    """
    chunks = retrieve(question, top_k=top_k)

    kwargs: dict[str, Any] = {"question": question, "chunks": chunks}
    if model:
        kwargs["model"] = model

    answer = generate(**kwargs)

    # Deduplicate sources while preserving insertion order
    seen: set[str] = set()
    sources: list[dict[str, Any]] = []
    for chunk in chunks:
        src = chunk["source"]
        if src not in seen:
            seen.add(src)
            sources.append(
                {
                    "source": src,
                    "doc_type": chunk["doc_type"],
                    "score": chunk["score"],
                }
            )

    return {
        "answer": answer,
        "sources": sources,
        "chunks_used": len(chunks),
    }
