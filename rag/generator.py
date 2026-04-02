"""LLM answer generator via Ollama."""

from __future__ import annotations

import os
import json
from typing import Any

import httpx

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mistral")
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "120"))

_SYSTEM_PROMPT = """You are Polymath, a precise research assistant.
Answer the user's question using ONLY the provided context chunks.
Rules:
1. Cite your sources by including [Source: <filename>] after any claim drawn from that source.
2. If the context does not contain enough information to answer, say "I don't have enough information in the provided documents to answer this."
3. Do not speculate or use outside knowledge.
4. Be concise and factual."""

_USER_TEMPLATE = """Context chunks:
{context}

Question: {question}

Answer (cite sources inline):"""


def _build_prompt(question: str, chunks: list[dict[str, Any]]) -> str:
    """Assemble the RAG prompt from retrieved chunks."""
    context_parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[{i}] (Source: {chunk['source']})\n{chunk['text']}"
        )
    context = "\n\n".join(context_parts)
    return _USER_TEMPLATE.format(context=context, question=question)


def generate(
    question: str,
    chunks: list[dict[str, Any]],
    model: str = OLLAMA_MODEL,
) -> str:
    """
    Generate an answer from retrieved context using Ollama.

    Parameters
    ----------
    question : str
        The user's question.
    chunks : list[dict]
        Retrieved context chunks from the retriever.
    model : str
        Ollama model name.

    Returns
    -------
    str
        The generated answer text.

    Raises
    ------
    httpx.HTTPError
        If Ollama is unreachable or returns an error.
    """
    if not chunks:
        return (
            "No relevant documents found in the knowledge base. "
            "Please ingest some documents first."
        )

    prompt = _build_prompt(question, chunks)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }

    with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
        response = client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
        )
        response.raise_for_status()

    data = response.json()
    return data["message"]["content"].strip()
