"""Tests for the FastAPI REST API endpoints."""

from __future__ import annotations

import sys
import io
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from api.main import app
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_ok(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert "chunker" in data
        assert "version" in data


class TestSourcesEndpoint:
    def test_sources_empty(self, client, tmp_path, monkeypatch):
        monkeypatch.setenv("VECTORSTORE_PATH", str(tmp_path / "vs_api"))
        import importlib
        import ingestion.store as store_mod
        importlib.reload(store_mod)

        with patch("api.main.list_sources", return_value=[]):
            res = client.get("/sources")
        assert res.status_code == 200
        data = res.json()
        assert data["total_documents"] == 0
        assert data["sources"] == []

    def test_sources_with_data(self, client):
        mock_sources = [
            {"source": "paper.pdf", "doc_type": "pdf", "chunk_count": 42},
            {"source": "notes.md", "doc_type": "markdown", "chunk_count": 8},
        ]
        with patch("api.main.list_sources", return_value=mock_sources):
            res = client.get("/sources")
        assert res.status_code == 200
        data = res.json()
        assert data["total_documents"] == 2
        assert data["total_chunks"] == 50


class TestQueryEndpoint:
    def test_query_returns_answer(self, client):
        mock_result = {
            "answer": "The sky is blue due to Rayleigh scattering.",
            "sources": [{"source": "physics.pdf", "doc_type": "pdf", "score": 0.92}],
            "chunks_used": 3,
        }
        with patch("api.main.run_query", return_value=mock_result):
            res = client.post("/query", json={"question": "Why is the sky blue?"})
        assert res.status_code == 200
        data = res.json()
        assert "answer" in data
        assert "sources" in data
        assert data["chunks_used"] == 3

    def test_query_validation_empty_question(self, client):
        res = client.post("/query", json={"question": ""})
        assert res.status_code == 422

    def test_query_top_k_validation(self, client):
        # top_k must be between 1 and 20
        res = client.post("/query", json={"question": "test", "top_k": 0})
        assert res.status_code == 422
        res = client.post("/query", json={"question": "test", "top_k": 21})
        assert res.status_code == 422


class TestIngestEndpoint:
    def test_ingest_markdown_file(self, client, tmp_path):
        md = tmp_path / "sample.md"
        md.write_text("# Test\n\nThis is a test document.\n")

        mock_result = {
            "source": "sample.md",
            "doc_type": "markdown",
            "chunks_stored": 2,
            "chunker_used": "python_fallback",
        }
        with patch("api.main.ingest_document", return_value=mock_result):
            with open(str(md), "rb") as f:
                res = client.post(
                    "/ingest",
                    files={"file": ("sample.md", f, "text/markdown")},
                )
        assert res.status_code == 200
        data = res.json()
        assert data["chunks_stored"] == 2
        assert "message" in data

    def test_ingest_unsupported_type(self, client, tmp_path):
        bad = tmp_path / "data.xyz"
        bad.write_text("some data")

        with patch("api.main.ingest_document", side_effect=ValueError("Unsupported file type")):
            with open(str(bad), "rb") as f:
                res = client.post(
                    "/ingest",
                    files={"file": ("data.xyz", f, "application/octet-stream")},
                )
        assert res.status_code == 400
