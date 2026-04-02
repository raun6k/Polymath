"""Tests for the ingestion pipeline (parsers, embedder, store, orchestrator)."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ── Parser tests ──────────────────────────────────────────────────────────────

class TestParsers:
    def test_parse_markdown_basic(self, tmp_path):
        from ingestion.parsers import parse_markdown

        md = tmp_path / "doc.md"
        md.write_text("# Title\n\nSome **bold** text and a [link](http://example.com).\n")
        text = parse_markdown(str(md))

        assert "Title" in text
        assert "bold" in text
        assert "link" in text
        # Markdown markers should be stripped
        assert "**" not in text
        assert "#" not in text

    def test_parse_markdown_code_fences_removed(self, tmp_path):
        from ingestion.parsers import parse_markdown

        md = tmp_path / "doc.md"
        md.write_text("Intro.\n\n```python\nx = 1\n```\n\nOutro.\n")
        text = parse_markdown(str(md))
        assert "Intro" in text
        assert "Outro" in text
        assert "x = 1" not in text

    def test_parse_code(self, tmp_path):
        from ingestion.parsers import parse_code

        src = tmp_path / "script.py"
        content = "def hello():\n    return 'world'\n"
        src.write_text(content)
        text = parse_code(str(src))
        assert text == content

    def test_parse_document_unsupported(self, tmp_path):
        from ingestion.parsers import parse_document

        f = tmp_path / "file.xyz"
        f.write_text("data")
        with pytest.raises(ValueError, match="Unsupported file type"):
            parse_document(str(f))

    def test_parse_document_dispatch(self, tmp_path):
        from ingestion.parsers import parse_document

        md = tmp_path / "readme.md"
        md.write_text("# Hello\n\nWorld.\n")
        text, doc_type = parse_document(str(md))
        assert doc_type == "markdown"
        assert "Hello" in text


# ── Embedder tests ────────────────────────────────────────────────────────────

class TestEmbedder:
    def test_embed_texts_returns_list(self):
        from ingestion.embedder import embed_texts

        vecs = embed_texts(["hello world", "foo bar"])
        assert len(vecs) == 2
        assert len(vecs[0]) > 0
        assert isinstance(vecs[0][0], float)

    def test_embed_empty_list(self):
        from ingestion.embedder import embed_texts

        assert embed_texts([]) == []

    def test_embed_query(self):
        from ingestion.embedder import embed_query

        vec = embed_query("test query")
        assert isinstance(vec, list)
        assert len(vec) > 0


# ── Store tests ───────────────────────────────────────────────────────────────

class TestStore:
    def test_store_and_list_sources(self, tmp_path, monkeypatch):
        monkeypatch.setenv("VECTORSTORE_PATH", str(tmp_path / "vs"))
        # Re-import to pick up env var
        import importlib
        import ingestion.store as store_mod
        importlib.reload(store_mod)

        from ingestion.embedder import embed_texts

        texts = ["Alpha beta gamma.", "Delta epsilon zeta."]
        embeddings = embed_texts(texts)
        n = store_mod.store_chunks(texts, embeddings, source="test.md", doc_type="markdown")
        assert n == 2

        sources = store_mod.list_sources()
        assert any(s["source"] == "test.md" for s in sources)

    def test_query_collection(self, tmp_path, monkeypatch):
        monkeypatch.setenv("VECTORSTORE_PATH", str(tmp_path / "vs2"))
        import importlib
        import ingestion.store as store_mod
        importlib.reload(store_mod)

        from ingestion.embedder import embed_texts, embed_query

        texts = ["The sky is blue.", "Grass is green."]
        embeddings = embed_texts(texts)
        store_mod.store_chunks(texts, embeddings, source="nature.md", doc_type="markdown")

        q_vec = embed_query("What color is the sky?")
        result = store_mod.query_collection(q_vec, n_results=1)
        assert result["documents"]
        assert "blue" in result["documents"][0][0].lower()


# ── Orchestrator tests ─────────────────────────────────────────────────────────

class TestOrchestrator:
    def test_ingest_markdown(self, tmp_path, monkeypatch):
        monkeypatch.setenv("VECTORSTORE_PATH", str(tmp_path / "vs3"))

        import importlib
        import ingestion.store as store_mod
        importlib.reload(store_mod)

        from ingestion.orchestrator import ingest_document

        md = tmp_path / "sample.md"
        md.write_text(
            "# Machine Learning\n\n"
            "Machine learning is a subset of artificial intelligence. "
            "It enables systems to learn from data. "
            "Supervised learning uses labeled training data.\n"
        )
        result = ingest_document(str(md))

        assert result["doc_type"] == "markdown"
        assert result["chunks_stored"] >= 1
        assert result["chunker_used"] in ("cpp", "python_fallback")
