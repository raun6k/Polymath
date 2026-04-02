"""Ingestion pipeline: parse → chunk → embed → store."""
from .orchestrator import ingest_document

__all__ = ["ingest_document"]
