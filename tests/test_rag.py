"""Tests for the RAG retriever (generator tests require Ollama running)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestRetriever:
    def test_retrieve_returns_list(self, tmp_path, monkeypatch):
        monkeypatch.setenv("VECTORSTORE_PATH", str(tmp_path / "vs_rag"))

        import importlib
        import ingestion.store as store_mod
        importlib.reload(store_mod)

        from ingestion.embedder import embed_texts
        from rag.retriever import retrieve

        # Populate the store
        texts = [
            "Photosynthesis converts sunlight into chemical energy.",
            "Mitosis is the process of cell division.",
            "Gravity is a fundamental force of nature.",
        ]
        embeddings = embed_texts(texts)
        store_mod.store_chunks(texts, embeddings, source="bio.md", doc_type="markdown")

        results = retrieve("How do plants make energy?", top_k=2)
        assert isinstance(results, list)
        assert len(results) <= 2
        for r in results:
            assert "text" in r
            assert "source" in r
            assert "score" in r
            assert 0.0 <= r["score"] <= 1.0

    def test_retrieve_top_k_respected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("VECTORSTORE_PATH", str(tmp_path / "vs_rag2"))

        import importlib
        import ingestion.store as store_mod
        importlib.reload(store_mod)

        from ingestion.embedder import embed_texts
        from rag.retriever import retrieve

        texts = [f"Sentence {i} about topic {i}." for i in range(10)]
        embeddings = embed_texts(texts)
        store_mod.store_chunks(texts, embeddings, source="multi.md", doc_type="markdown")

        results = retrieve("something", top_k=3)
        assert len(results) <= 3

    def test_retrieve_sorted_by_score(self, tmp_path, monkeypatch):
        monkeypatch.setenv("VECTORSTORE_PATH", str(tmp_path / "vs_rag3"))

        import importlib
        import ingestion.store as store_mod
        importlib.reload(store_mod)

        from ingestion.embedder import embed_texts
        from rag.retriever import retrieve

        texts = [
            "Deep learning uses neural networks.",
            "Cooking pasta requires boiling water.",
            "Neural networks have layers and weights.",
        ]
        embeddings = embed_texts(texts)
        store_mod.store_chunks(texts, embeddings, source="ml.md", doc_type="markdown")

        results = retrieve("What is a neural network?", top_k=3)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)
