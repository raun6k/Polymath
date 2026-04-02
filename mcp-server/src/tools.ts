/**
 * Tool implementations for the Polymath MCP server.
 * Each function calls the Python REST API via HTTP fetch.
 */

import { readFileSync } from "fs";
import { join } from "path";

const API_BASE = process.env.POLYMATH_API_URL ?? "http://localhost:8000";

interface SearchResult {
  answer: string;
  sources: Array<{ source: string; doc_type: string; score: number }>;
  chunks_used: number;
}

interface IngestResult {
  source: string;
  doc_type: string;
  chunks_stored: number;
  chunker_used: string;
  message: string;
}

interface SourcesResult {
  sources: Array<{ source: string; doc_type: string; chunk_count: number }>;
  total_documents: number;
  total_chunks: number;
}

// ── search_knowledge_base ─────────────────────────────────────────────────────

export async function searchKnowledgeBase(
  question: string,
  topK: number = 5
): Promise<string> {
  const response = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API error ${response.status}: ${error}`);
  }

  const data = (await response.json()) as SearchResult;

  const sourceLines = data.sources
    .map(
      (s) =>
        `  - ${s.source} (${s.doc_type}, relevance: ${(s.score * 100).toFixed(1)}%)`
    )
    .join("\n");

  return [
    `**Answer:**\n${data.answer}`,
    "",
    `**Sources used (${data.chunks_used} chunks from ${data.sources.length} documents):**`,
    sourceLines || "  (none)",
  ].join("\n");
}

// ── ingest_document ───────────────────────────────────────────────────────────

export async function ingestDocument(filePath: string): Promise<string> {
  // Read the file and POST it as multipart/form-data
  let fileBuffer: Buffer;
  try {
    fileBuffer = readFileSync(filePath);
  } catch (err) {
    throw new Error(`Cannot read file: ${filePath} — ${(err as Error).message}`);
  }

  const fileName = filePath.split("/").pop() ?? "document";

  const formData = new FormData();
  const blob = new Blob([fileBuffer]);
  formData.append("file", blob, fileName);

  const response = await fetch(`${API_BASE}/ingest`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Ingest API error ${response.status}: ${error}`);
  }

  const data = (await response.json()) as IngestResult;

  return [
    `**Ingestion complete:**`,
    `  File: ${data.source}`,
    `  Type: ${data.doc_type}`,
    `  Chunks stored: ${data.chunks_stored}`,
    `  Chunker: ${data.chunker_used}`,
    `  ${data.message}`,
  ].join("\n");
}

// ── list_sources ──────────────────────────────────────────────────────────────

export async function listSources(): Promise<string> {
  const response = await fetch(`${API_BASE}/sources`);

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Sources API error ${response.status}: ${error}`);
  }

  const data = (await response.json()) as SourcesResult;

  if (data.total_documents === 0) {
    return "No documents have been ingested yet. Use `ingest_document` to add documents.";
  }

  const rows = data.sources
    .map((s) => `  - ${s.source} (${s.doc_type}): ${s.chunk_count} chunks`)
    .join("\n");

  return [
    `**Ingested documents (${data.total_documents} total, ${data.total_chunks} chunks):**`,
    rows,
  ].join("\n");
}
