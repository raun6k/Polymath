"""Embedding model wrapper using sentence-transformers (all-MiniLM-L6-v2)."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

import os

MODEL_NAME = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")


@lru_cache(maxsize=1)
def _get_model():
    """Lazy-load the sentence-transformer model (cached singleton)."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of text strings.

    Parameters
    ----------
    texts : list[str]
        Texts to embed.

    Returns
    -------
    list[list[float]]
        One embedding vector per input text.
    """
    if not texts:
        return []
    model = _get_model()
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """Embed a single query string."""
    return embed_texts([query])[0]
