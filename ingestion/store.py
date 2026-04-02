"""ChromaDB vector store interface."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

import chromadb

VECTORSTORE_PATH = os.environ.get("VECTORSTORE_PATH", "./vectorstore")
COLLECTION_NAME = os.environ.get("CHROMA_COLLECTION", "polymath")


def _get_client() -> chromadb.PersistentClient:
    """Return a persistent ChromaDB client (creates DB dir if needed)."""
    Path(VECTORSTORE_PATH).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=VECTORSTORE_PATH)


def _get_collection(client: chromadb.PersistentClient | None = None):
    """Return (or create) the main Polymath collection."""
    if client is None:
        client = _get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def store_chunks(
    chunks_text: list[str],
    embeddings: list[list[float]],
    source: str,
    doc_type: str,
    extra_metadata: dict[str, Any] | None = None,
) -> int:
    """
    Persist a batch of chunk embeddings to ChromaDB.

    Parameters
    ----------
    chunks_text : list[str]
        The raw text of each chunk.
    embeddings : list[list[float]]
        Corresponding embedding vectors.
    source : str
        Original document path/name used as source attribution.
    doc_type : str
        One of 'pdf', 'markdown', 'code'.
    extra_metadata : dict | None
        Any additional metadata to store alongside each chunk.

    Returns
    -------
    int
        Number of chunks stored.
    """
    if not chunks_text:
        return 0

    collection = _get_collection()

    ids = [str(uuid.uuid4()) for _ in chunks_text]
    metadatas = []
    for i, text in enumerate(chunks_text):
        meta: dict[str, Any] = {
            "source": source,
            "doc_type": doc_type,
            "chunk_index": i,
            "chunk_count": len(chunks_text),
        }
        if extra_metadata:
            meta.update(extra_metadata)
        metadatas.append(meta)

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks_text,
        metadatas=metadatas,
    )
    return len(chunks_text)


def list_sources() -> list[dict[str, Any]]:
    """
    Return a list of all ingested source documents with chunk counts.

    Returns
    -------
    list[dict]
        Each dict has keys: source, doc_type, chunk_count.
    """
    collection = _get_collection()
    result = collection.get(include=["metadatas"])

    # Aggregate by source
    source_info: dict[str, dict[str, Any]] = {}
    for meta in result.get("metadatas") or []:
        src = meta.get("source", "unknown")
        if src not in source_info:
            source_info[src] = {
                "source": src,
                "doc_type": meta.get("doc_type", "unknown"),
                "chunk_count": 0,
            }
        source_info[src]["chunk_count"] += 1

    return list(source_info.values())


def query_collection(
    query_embedding: list[float],
    n_results: int = 5,
    where: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Run a vector similarity search.

    Parameters
    ----------
    query_embedding : list[float]
        The query vector.
    n_results : int
        How many results to return.
    where : dict | None
        Optional ChromaDB metadata filter.

    Returns
    -------
    dict
        Raw ChromaDB query result with keys: ids, documents, metadatas, distances.
    """
    collection = _get_collection()
    kwargs: dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": min(n_results, max(collection.count(), 1)),
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where
    return collection.query(**kwargs)


def delete_source(source: str) -> int:
    """Delete all chunks associated with a source document."""
    collection = _get_collection()
    results = collection.get(where={"source": source}, include=[])
    ids = results.get("ids", [])
    if ids:
        collection.delete(ids=ids)
    return len(ids)
