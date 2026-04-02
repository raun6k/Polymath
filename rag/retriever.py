"""Vector similarity retriever backed by ChromaDB."""

from __future__ import annotations

import os
from typing import Any

from ingestion.embedder import embed_query
from ingestion.store import query_collection

TOP_K = int(os.environ.get("RETRIEVER_TOP_K", "5"))


def retrieve(
    question: str,
    top_k: int = TOP_K,
    where: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve the top-k most relevant chunks for a question.

    Parameters
    ----------
    question : str
        The user's natural-language question.
    top_k : int
        Number of chunks to retrieve.
    where : dict | None
        Optional metadata filter (passed to ChromaDB).

    Returns
    -------
    list[dict]
        Each dict: {'text', 'source', 'doc_type', 'score', 'chunk_index'}.
    """
    query_vec = embed_query(question)
    raw = query_collection(query_vec, n_results=top_k, where=where)

    results: list[dict[str, Any]] = []
    docs = (raw.get("documents") or [[]])[0]
    metas = (raw.get("metadatas") or [[]])[0]
    dists = (raw.get("distances") or [[]])[0]

    for doc, meta, dist in zip(docs, metas, dists):
        # ChromaDB cosine distance: 0 = identical, 2 = opposite
        score = 1.0 - (dist / 2.0)
        results.append(
            {
                "text": doc,
                "source": meta.get("source", "unknown"),
                "doc_type": meta.get("doc_type", "unknown"),
                "score": round(score, 4),
                "chunk_index": meta.get("chunk_index", 0),
            }
        )

    # Sort by descending relevance score
    results.sort(key=lambda x: x["score"], reverse=True)
    return results
