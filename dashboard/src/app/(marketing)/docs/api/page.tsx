"use client";

import { useState, useCallback } from "react";

export default function DocsApiPage() {
  return (
    <article style={{ animation: "drift-up 400ms ease both" }}>
      <h1
        className="text-[36px] font-normal tracking-tight mb-3"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        API Reference
      </h1>
      <p
        className="text-[16px] leading-[1.65] mb-10 max-w-2xl"
        style={{ color: "var(--muted)" }}
      >
        CMK exposes a REST API on the configured port. All endpoints accept
        and return JSON. Authentication is optional and configured via API
        keys.
      </p>

      <div
        className="rounded-[var(--radius)] p-4 mb-10"
        style={{
          background: "var(--warm-paper)",
          border: "1px solid var(--border-light)",
        }}
      >
        <p
          className="text-[13px] leading-[1.5]"
          style={{ color: "var(--muted)" }}
        >
          Base URL:{" "}
          <code style={inlineCodeStyle}>http://localhost:7749</code>. All
          paths below are relative to this base.
        </p>
      </div>

      {/* Endpoints */}
      <div className="space-y-10">
        {ENDPOINTS.map((endpoint, i) => (
          <EndpointSection key={i} endpoint={endpoint} />
        ))}
      </div>
    </article>
  );
}

function EndpointSection({ endpoint }: { endpoint: Endpoint }) {
  return (
    <section>
      <div className="flex items-center gap-3 mb-3">
        <span
          className="px-2.5 py-1 rounded-[4px] text-[12px] font-bold font-mono uppercase"
          style={{
            background: METHOD_COLORS[endpoint.method].bg,
            color: METHOD_COLORS[endpoint.method].fg,
          }}
        >
          {endpoint.method}
        </span>
        <code
          className="text-[14px] font-mono font-medium"
          style={{ color: "var(--foreground)" }}
        >
          {endpoint.path}
        </code>
      </div>
      <p
        className="text-[14px] leading-[1.65] mb-4"
        style={{ color: "var(--muted)" }}
      >
        {endpoint.description}
      </p>

      {endpoint.body && (
        <div className="mb-4">
          <p
            className="text-[12px] font-medium uppercase tracking-wider mb-2"
            style={{ color: "var(--muted-light)" }}
          >
            Request body
          </p>
          <CodeBlock code={endpoint.body} />
        </div>
      )}

      {endpoint.response && (
        <div>
          <p
            className="text-[12px] font-medium uppercase tracking-wider mb-2"
            style={{ color: "var(--muted-light)" }}
          >
            Response
          </p>
          <CodeBlock code={endpoint.response} />
        </div>
      )}

      {endpoint.params && (
        <div className="mb-4">
          <p
            className="text-[12px] font-medium uppercase tracking-wider mb-2"
            style={{ color: "var(--muted-light)" }}
          >
            Parameters
          </p>
          <div
            className="rounded-[var(--radius-sm)] overflow-hidden"
            style={{ border: "1px solid var(--border-light)" }}
          >
            {endpoint.params.map((param, i) => (
              <div
                key={i}
                className="flex items-start gap-3 px-4 py-2.5"
                style={{
                  borderBottom:
                    i < endpoint.params!.length - 1
                      ? "1px solid var(--border-light)"
                      : "none",
                  background:
                    i % 2 === 0 ? "var(--surface)" : "var(--background)",
                }}
              >
                <code
                  className="text-[12px] font-mono font-medium shrink-0"
                  style={{ color: "var(--foreground)" }}
                >
                  {param.name}
                </code>
                <span
                  className="text-[11px] font-mono shrink-0"
                  style={{ color: "var(--muted-light)" }}
                >
                  {param.type}
                </span>
                <span
                  className="text-[12px]"
                  style={{ color: "var(--muted)" }}
                >
                  {param.desc}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function CodeBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }, [code]);

  return (
    <div
      className="rounded-[var(--radius)] overflow-hidden"
      style={{
        background: "var(--code-bg)",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      <div
        className="flex items-center justify-end px-4 py-2"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}
      >
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-[var(--radius-sm)] text-[11px] font-medium"
          style={{
            color: copied
              ? "var(--gate-promissory)"
              : "rgba(231, 229, 228, 0.5)",
            background: copied
              ? "rgba(5, 150, 105, 0.15)"
              : "rgba(255, 255, 255, 0.05)",
            transition: "all 140ms ease",
          }}
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre
        className="p-4 overflow-x-auto text-[13px] leading-[1.6] font-mono"
        style={{ color: "var(--code-fg)" }}
      >
        <code>{code}</code>
      </pre>
    </div>
  );
}

const METHOD_COLORS: Record<string, { bg: string; fg: string }> = {
  GET: { bg: "rgba(5, 150, 105, 0.1)", fg: "var(--success)" },
  POST: { bg: "rgba(37, 99, 235, 0.1)", fg: "var(--gate-relational)" },
  PUT: { bg: "rgba(217, 119, 6, 0.1)", fg: "var(--gate-behavioral)" },
  PATCH: { bg: "rgba(124, 58, 237, 0.1)", fg: "var(--gate-epistemic)" },
  DELETE: { bg: "rgba(220, 38, 38, 0.1)", fg: "var(--gate-correction)" },
};

type Param = { name: string; type: string; desc: string };

type Endpoint = {
  method: string;
  path: string;
  description: string;
  body?: string;
  response?: string;
  params?: Param[];
};

const ENDPOINTS: Endpoint[] = [
  {
    method: "GET",
    path: "/api/memories",
    description:
      "List all memories. Supports filtering by gate, scope, and pagination.",
    params: [
      { name: "gate", type: "string?", desc: "Filter by gate type" },
      { name: "scope", type: "string?", desc: "Filter by scope (user, project, global)" },
      { name: "limit", type: "int?", desc: "Max results (default 50)" },
      { name: "offset", type: "int?", desc: "Pagination offset (default 0)" },
    ],
    response: `{
  "memories": [
    {
      "id": "mem_abc123",
      "content": "User prefers VS Code",
      "gate": "behavioral",
      "scope": "user",
      "confidence": 92,
      "created_at": "2026-01-15T10:30:00Z"
    }
  ],
  "total": 147
}`,
  },
  {
    method: "POST",
    path: "/api/memories",
    description:
      "Create a new memory. The gate is auto-classified if not provided.",
    body: `{
  "content": "We use PostgreSQL 16 for all services",
  "gate": "epistemic",
  "scope": "project"
}`,
    response: `{
  "id": "mem_def456",
  "content": "We use PostgreSQL 16 for all services",
  "gate": "epistemic",
  "scope": "project",
  "confidence": 85,
  "created_at": "2026-02-14T09:00:00Z"
}`,
  },
  {
    method: "POST",
    path: "/api/search",
    description:
      "Semantic search across memories. Returns ranked results with confidence scores.",
    body: `{
  "query": "preferred database",
  "limit": 5,
  "gate": null,
  "min_confidence": 50
}`,
    response: `{
  "results": [
    {
      "id": "mem_def456",
      "content": "We use PostgreSQL 16 for all services",
      "gate": "epistemic",
      "confidence": 85,
      "similarity": 0.94
    }
  ]
}`,
  },
  {
    method: "GET",
    path: "/api/identity",
    description:
      "Retrieve the current identity synthesis document. This is a generated summary of the user based on stored memories.",
    response: `{
  "identity": "You are a senior TypeScript developer...",
  "updated_at": "2026-02-14T08:00:00Z",
  "memory_count": 47
}`,
  },
  {
    method: "PUT",
    path: "/api/identity",
    description: "Replace the identity document with a new synthesis.",
    body: `{
  "identity": "Updated identity text..."
}`,
    response: `{
  "identity": "Updated identity text...",
  "updated_at": "2026-02-14T09:30:00Z"
}`,
  },
  {
    method: "PATCH",
    path: "/api/memories/{id}",
    description:
      "Update a specific memory. Supports editing content, gate, scope, and confidence.",
    params: [
      { name: "id", type: "string", desc: "Memory ID (path parameter)" },
    ],
    body: `{
  "content": "Updated memory content",
  "confidence": 95
}`,
    response: `{
  "id": "mem_abc123",
  "content": "Updated memory content",
  "confidence": 95,
  "updated_at": "2026-02-14T10:00:00Z"
}`,
  },
  {
    method: "POST",
    path: "/api/memories/{id}/pin",
    description:
      "Pin a memory to prevent decay. Pinned memories maintain their confidence indefinitely.",
    params: [
      { name: "id", type: "string", desc: "Memory ID (path parameter)" },
    ],
    response: `{
  "id": "mem_abc123",
  "pinned": true
}`,
  },
  {
    method: "DELETE",
    path: "/api/memories/{id}/pin",
    description:
      "Unpin a memory. It will resume normal decay behavior from its current confidence.",
    params: [
      { name: "id", type: "string", desc: "Memory ID (path parameter)" },
    ],
    response: `{
  "id": "mem_abc123",
  "pinned": false
}`,
  },
  {
    method: "GET",
    path: "/api/stats",
    description:
      "Get memory statistics: total count, breakdown by gate, average confidence, storage usage.",
    response: `{
  "total": 147,
  "by_gate": {
    "behavioral": 42,
    "relational": 18,
    "epistemic": 53,
    "promissory": 21,
    "correction": 13
  },
  "avg_confidence": 78.4,
  "storage_bytes": 2457600
}`,
  },
  {
    method: "POST",
    path: "/api/reflect",
    description:
      "Trigger a reflection cycle. CMK reviews recent memories, resolves contradictions, and updates the identity document.",
    response: `{
  "resolved": 3,
  "decayed": 7,
  "identity_updated": true
}`,
  },
  {
    method: "GET",
    path: "/api/mode",
    description:
      "Get the current storage mode (local or cloud).",
    response: `{
  "mode": "local",
  "storage": "sqlite",
  "embeddings": "fastembed"
}`,
  },
  {
    method: "GET",
    path: "/api/keys",
    description:
      "List all API keys. Keys are masked in the response.",
    response: `{
  "keys": [
    {
      "id": "key_001",
      "name": "development",
      "prefix": "cmk_dev_****",
      "created_at": "2026-01-10T12:00:00Z"
    }
  ]
}`,
  },
  {
    method: "POST",
    path: "/api/keys",
    description:
      "Create a new API key. The full key is only returned once at creation time.",
    body: `{
  "name": "production"
}`,
    response: `{
  "id": "key_002",
  "name": "production",
  "key": "cmk_prod_abc123def456",
  "created_at": "2026-02-14T10:00:00Z"
}`,
  },
  {
    method: "DELETE",
    path: "/api/keys/{key_id}",
    description: "Revoke an API key. This action is irreversible.",
    params: [
      { name: "key_id", type: "string", desc: "API key ID (path parameter)" },
    ],
    response: `{
  "deleted": true
}`,
  },
];

const inlineCodeStyle: React.CSSProperties = {
  background: "var(--warm-paper)",
  padding: "1px 5px",
  borderRadius: 4,
  fontSize: "12px",
  fontFamily: "var(--font-mono)",
  color: "var(--foreground)",
};
