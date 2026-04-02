#!/usr/bin/env node
/**
 * Polymath MCP Server
 *
 * Implements the Model Context Protocol so any MCP-compatible AI client
 * (Claude, Cursor, etc.) can use the Polymath knowledge base as a first-class tool.
 *
 * Transport: StdioServerTransport (JSON-RPC over stdin/stdout)
 * Tools: search_knowledge_base, ingest_document, list_sources
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";

import {
  searchKnowledgeBase,
  ingestDocument,
  listSources,
} from "./tools.js";

// ── Tool definitions ──────────────────────────────────────────────────────────

const TOOLS: Tool[] = [
  {
    name: "search_knowledge_base",
    description:
      "Search the Polymath knowledge base and get an AI-generated answer with source citations. " +
      "Use this to answer questions about ingested documents (PDFs, Markdown files, code).",
    inputSchema: {
      type: "object",
      properties: {
        question: {
          type: "string",
          description: "The natural-language question to answer",
        },
        top_k: {
          type: "number",
          description: "Number of document chunks to retrieve (default: 5, max: 20)",
          minimum: 1,
          maximum: 20,
        },
      },
      required: ["question"],
    },
  },
  {
    name: "ingest_document",
    description:
      "Ingest a document file (PDF, Markdown, or code) into the Polymath knowledge base. " +
      "After ingestion, the document's contents become searchable via search_knowledge_base.",
    inputSchema: {
      type: "object",
      properties: {
        file_path: {
          type: "string",
          description: "Absolute path to the document file on the server",
        },
      },
      required: ["file_path"],
    },
  },
  {
    name: "list_sources",
    description:
      "List all documents currently ingested in the Polymath knowledge base, " +
      "including their file types and chunk counts.",
    inputSchema: {
      type: "object",
      properties: {},
      required: [],
    },
  },
];

// ── Server setup ──────────────────────────────────────────────────────────────

const server = new Server(
  {
    name: "polymath",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// tools/list handler
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: TOOLS,
}));

// tools/call handler
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    let text: string;

    switch (name) {
      case "search_knowledge_base": {
        const question = args?.question as string;
        const topK = (args?.top_k as number | undefined) ?? 5;
        if (!question) throw new Error("'question' argument is required");
        text = await searchKnowledgeBase(question, topK);
        break;
      }

      case "ingest_document": {
        const filePath = args?.file_path as string;
        if (!filePath) throw new Error("'file_path' argument is required");
        text = await ingestDocument(filePath);
        break;
      }

      case "list_sources": {
        text = await listSources();
        break;
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }

    return {
      content: [{ type: "text", text }],
    };
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Error: ${(error as Error).message}`,
        },
      ],
      isError: true,
    };
  }
});

// ── Start ─────────────────────────────────────────────────────────────────────

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // MCP servers communicate via stdio — stderr for logs
  process.stderr.write("Polymath MCP server running on stdio\n");
}

main().catch((err) => {
  process.stderr.write(`Fatal error: ${err}\n`);
  process.exit(1);
});
