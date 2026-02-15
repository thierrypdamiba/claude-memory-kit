"use client";

import { useState, useCallback } from "react";

export default function DocsCliPage() {
  return (
    <article style={{ animation: "drift-up 400ms ease both" }}>
      <h1
        className="text-[36px] font-normal tracking-tight mb-3"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        CLI Reference
      </h1>
      <p
        className="text-[16px] leading-[1.65] mb-10 max-w-2xl"
        style={{ color: "var(--muted)" }}
      >
        The <code style={inlineCodeStyle}>cmk</code> command line tool lets
        you manage memories, run the MCP server, and interact with the memory
        store directly from your terminal.
      </p>

      {/* Commands */}
      <div className="space-y-10">
        {COMMANDS.map((cmd, i) => (
          <section key={i}>
            <div className="flex items-center gap-3 mb-3">
              <code
                className="text-[15px] font-mono font-semibold"
                style={{ color: "var(--foreground)" }}
              >
                cmk {cmd.name}
              </code>
            </div>
            <p
              className="text-[14px] leading-[1.65] mb-4"
              style={{ color: "var(--muted)" }}
            >
              {cmd.description}
            </p>

            <CodeBlock code={cmd.usage} />

            {cmd.flags && cmd.flags.length > 0 && (
              <div className="mt-4">
                <p
                  className="text-[12px] font-medium uppercase tracking-wider mb-2"
                  style={{ color: "var(--muted-light)" }}
                >
                  Options
                </p>
                <div
                  className="rounded-[var(--radius-sm)] overflow-hidden"
                  style={{ border: "1px solid var(--border-light)" }}
                >
                  {cmd.flags.map((flag, j) => (
                    <div
                      key={j}
                      className="flex items-start gap-4 px-4 py-2.5"
                      style={{
                        borderBottom:
                          j < cmd.flags!.length - 1
                            ? "1px solid var(--border-light)"
                            : "none",
                        background:
                          j % 2 === 0
                            ? "var(--surface)"
                            : "var(--background)",
                      }}
                    >
                      <code
                        className="text-[12px] font-mono font-medium shrink-0"
                        style={{ color: "var(--foreground)", minWidth: 160 }}
                      >
                        {flag.flag}
                      </code>
                      <span
                        className="text-[12px]"
                        style={{ color: "var(--muted)" }}
                      >
                        {flag.desc}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {cmd.examples && cmd.examples.length > 0 && (
              <div className="mt-4">
                <p
                  className="text-[12px] font-medium uppercase tracking-wider mb-2"
                  style={{ color: "var(--muted-light)" }}
                >
                  Examples
                </p>
                <div className="space-y-2">
                  {cmd.examples.map((ex, j) => (
                    <div key={j}>
                      <p
                        className="text-[12px] mb-1"
                        style={{ color: "var(--muted)" }}
                      >
                        {ex.desc}
                      </p>
                      <CodeBlock code={ex.code} />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        ))}
      </div>
    </article>
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

type Flag = { flag: string; desc: string };
type Example = { desc: string; code: string };

type Command = {
  name: string;
  description: string;
  usage: string;
  flags?: Flag[];
  examples?: Example[];
};

const COMMANDS: Command[] = [
  {
    name: "serve",
    description:
      "Start the CMK MCP server. This is the primary way to run CMK. The server exposes both the MCP tool interface and the REST API.",
    usage: "cmk serve [OPTIONS]",
    flags: [
      { flag: "--port <PORT>", desc: "Port to listen on (default: 7749)" },
      {
        flag: "--storage <MODE>",
        desc: "Storage mode: local or cloud (default: local)",
      },
      { flag: "--host <HOST>", desc: "Bind address (default: 127.0.0.1)" },
      {
        flag: "--log-level <LEVEL>",
        desc: "Logging level: debug, info, warn, error (default: info)",
      },
    ],
    examples: [
      { desc: "Start with defaults:", code: "cmk serve" },
      {
        desc: "Start on a specific port with cloud storage:",
        code: "cmk serve --port 8842 --storage cloud",
      },
    ],
  },
  {
    name: "init",
    description:
      "Initialize the CMK data directory. Creates the SQLite database, default configuration, and local embeddings cache. Safe to run multiple times.",
    usage: "cmk init [OPTIONS]",
    flags: [
      {
        flag: "--dir <PATH>",
        desc: "Data directory path (default: ~/.cmk)",
      },
      {
        flag: "--storage <MODE>",
        desc: "Initial storage mode (default: local)",
      },
    ],
  },
  {
    name: "remember",
    description:
      "Store a memory directly from the command line. The gate is auto-classified if not specified.",
    usage: 'cmk remember "<CONTENT>" [OPTIONS]',
    flags: [
      {
        flag: "--gate <GATE>",
        desc: "Gate type: behavioral, relational, epistemic, promissory, correction",
      },
      {
        flag: "--scope <SCOPE>",
        desc: "Scope: user, project, global (default: user)",
      },
      { flag: "--pin", desc: "Pin this memory immediately" },
    ],
    examples: [
      {
        desc: "Remember a preference:",
        code: 'cmk remember "I prefer 2-space indentation" --gate behavioral',
      },
      {
        desc: "Remember a fact and pin it:",
        code: 'cmk remember "API uses JWT RS256" --gate epistemic --scope project --pin',
      },
    ],
  },
  {
    name: "recall",
    description:
      "Search memories using natural language. Returns ranked results with confidence scores and gate labels.",
    usage: 'cmk recall "<QUERY>" [OPTIONS]',
    flags: [
      { flag: "--limit <N>", desc: "Maximum results (default: 5)" },
      { flag: "--gate <GATE>", desc: "Filter by gate type" },
      {
        flag: "--min-confidence <N>",
        desc: "Minimum confidence threshold (default: 0)",
      },
      { flag: "--json", desc: "Output as JSON" },
    ],
    examples: [
      {
        desc: "Search for database preferences:",
        code: 'cmk recall "preferred database"',
      },
      {
        desc: "Search with filters and JSON output:",
        code: 'cmk recall "auth setup" --gate epistemic --limit 10 --json',
      },
    ],
  },
  {
    name: "reflect",
    description:
      "Trigger a reflection cycle. CMK reviews all memories, applies decay, resolves contradictions, and regenerates the identity document.",
    usage: "cmk reflect [OPTIONS]",
    flags: [
      { flag: "--dry-run", desc: "Preview changes without applying them" },
      { flag: "--verbose", desc: "Show detailed output for each resolved memory" },
    ],
  },
  {
    name: "forget",
    description:
      "Delete a specific memory by ID, or delete all memories matching a filter.",
    usage: "cmk forget <ID> [OPTIONS]",
    flags: [
      { flag: "--all", desc: "Delete all memories (requires confirmation)" },
      { flag: "--gate <GATE>", desc: "Delete all memories of a specific gate" },
      { flag: "--force", desc: "Skip confirmation prompt" },
    ],
    examples: [
      { desc: "Delete a specific memory:", code: "cmk forget mem_abc123" },
      {
        desc: "Delete all promissory memories:",
        code: "cmk forget --gate promissory --force",
      },
    ],
  },
  {
    name: "identity",
    description:
      "View or edit the identity synthesis document. Without arguments, prints the current identity.",
    usage: "cmk identity [OPTIONS]",
    flags: [
      {
        flag: "--edit",
        desc: "Open the identity document in your default editor",
      },
      { flag: "--regenerate", desc: "Regenerate the identity from all memories" },
      { flag: "--json", desc: "Output as JSON" },
    ],
    examples: [
      { desc: "View current identity:", code: "cmk identity" },
      {
        desc: "Regenerate from memories:",
        code: "cmk identity --regenerate",
      },
    ],
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
