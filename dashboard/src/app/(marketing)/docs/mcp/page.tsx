"use client";

import { useState, useCallback } from "react";

export default function DocsMcpPage() {
  return (
    <article style={{ animation: "drift-up 400ms ease both" }}>
      <h1
        className="text-[36px] font-normal tracking-tight mb-3"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        MCP Configuration
      </h1>
      <p
        className="text-[16px] leading-[1.65] mb-10 max-w-2xl"
        style={{ color: "var(--muted)" }}
      >
        CMK connects to Claude through the Model Context Protocol (MCP).
        Cloud mode uses our hosted endpoint. No local server needed.
      </p>

      {/* Cloud: Claude Code */}
      <section className="mb-12">
        <h2
          className="text-[20px] font-semibold tracking-tight mb-2"
          style={{ color: "var(--foreground)" }}
        >
          Claude Code
        </h2>
        <p
          className="text-[14px] leading-[1.65] mb-4"
          style={{ color: "var(--muted)" }}
        >
          One command. Paste your API key from the dashboard.
        </p>
        <CodeBlock
          label="terminal"
          code={`claude mcp add cmk --url https://mcp.cmk.dev/v1 \\
  --header "Authorization: Bearer <your-api-key>"`}
        />
      </section>

      {/* Cloud: Claude Desktop */}
      <section className="mb-12">
        <h2
          className="text-[20px] font-semibold tracking-tight mb-2"
          style={{ color: "var(--foreground)" }}
        >
          Claude Desktop
        </h2>
        <p
          className="text-[14px] leading-[1.65] mb-4"
          style={{ color: "var(--muted)" }}
        >
          Open Settings, then Developer, then Edit Config. Add this to your{" "}
          <code style={inlineCodeStyle}>claude_desktop_config.json</code>:
        </p>
        <CodeBlock
          label="claude_desktop_config.json"
          code={`{
  "mcpServers": {
    "cmk": {
      "url": "https://mcp.cmk.dev/v1",
      "headers": {
        "Authorization": "Bearer <your-api-key>"
      }
    }
  }
}`}
        />
        <div
          className="mt-5 rounded-[var(--radius)] p-4"
          style={{
            background: "var(--warm-paper)",
            border: "1px solid var(--border-light)",
          }}
        >
          <p
            className="text-[13px] leading-[1.6]"
            style={{ color: "var(--muted)" }}
          >
            Config file location by platform:
          </p>
          <div className="mt-2 space-y-1">
            <PathRow
              platform="macOS"
              path="~/Library/Application Support/Claude/claude_desktop_config.json"
            />
            <PathRow
              platform="Windows"
              path="%APPDATA%\\Claude\\claude_desktop_config.json"
            />
            <PathRow
              platform="Linux"
              path="~/.config/Claude/claude_desktop_config.json"
            />
          </div>
        </div>
      </section>

      {/* Self-hosted / Local */}
      <section className="mb-12">
        <div
          className="rounded-[var(--radius)] p-5"
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border-light)",
          }}
        >
          <details>
            <summary
              className="text-[14px] font-medium cursor-pointer"
              style={{ color: "var(--foreground)" }}
            >
              Self-hosted / local mode configuration
            </summary>
            <div className="mt-4 space-y-6">
              <p
                className="text-[13px] leading-[1.6]"
                style={{ color: "var(--muted)" }}
              >
                Run your own CMK server locally. Requires{" "}
                <code style={inlineCodeStyle}>pip install claude-memory-kit</code>.
              </p>

              <div>
                <p
                  className="text-[13px] font-medium mb-2"
                  style={{ color: "var(--foreground)" }}
                >
                  Claude Code (local)
                </p>
                <CodeBlock
                  label="terminal"
                  code={`claude mcp add cmk -- cmk serve --port 7749`}
                />
              </div>

              <div>
                <p
                  className="text-[13px] font-medium mb-2"
                  style={{ color: "var(--foreground)" }}
                >
                  Claude Desktop (local)
                </p>
                <CodeBlock
                  label="claude_desktop_config.json"
                  code={`{
  "mcpServers": {
    "cmk": {
      "command": "cmk",
      "args": ["serve", "--port", "7749"],
      "env": {
        "CMK_STORAGE": "local"
      }
    }
  }
}`}
                />
              </div>

              {/* Environment variables */}
              <div>
                <p
                  className="text-[13px] font-medium mb-3"
                  style={{ color: "var(--foreground)" }}
                >
                  Environment variables (self-hosted only)
                </p>
                <div
                  className="rounded-[var(--radius-lg)] overflow-hidden overflow-x-auto"
                  style={{
                    border: "1px solid var(--border)",
                    boxShadow: "var(--shadow-sm)",
                  }}
                >
                  <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr
                        style={{
                          background: "var(--warm-paper)",
                          borderBottom: "1px solid var(--border)",
                        }}
                      >
                        <th
                          className="text-left px-5 py-3 text-[13px] font-semibold"
                          style={{ color: "var(--foreground)" }}
                        >
                          Variable
                        </th>
                        <th
                          className="text-left px-5 py-3 text-[13px] font-semibold"
                          style={{ color: "var(--foreground)" }}
                        >
                          Description
                        </th>
                        <th
                          className="text-left px-5 py-3 text-[13px] font-semibold"
                          style={{ color: "var(--foreground)" }}
                        >
                          Default
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {ENV_VARS.map((v, i) => (
                        <tr
                          key={i}
                          style={{
                            borderBottom:
                              i < ENV_VARS.length - 1
                                ? "1px solid var(--border-light)"
                                : "none",
                            background:
                              i % 2 === 0 ? "var(--surface)" : "var(--background)",
                          }}
                        >
                          <td className="px-5 py-3">
                            <code
                              className="text-[12px] font-mono"
                              style={{
                                background: "var(--warm-paper)",
                                padding: "1px 5px",
                                borderRadius: 4,
                                color: "var(--foreground)",
                              }}
                            >
                              {v.name}
                            </code>
                          </td>
                          <td
                            className="px-5 py-3 text-[13px]"
                            style={{ color: "var(--muted)" }}
                          >
                            {v.description}
                          </td>
                          <td
                            className="px-5 py-3 text-[12px] font-mono"
                            style={{ color: "var(--muted-light)" }}
                          >
                            {v.defaultValue}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </details>
        </div>
      </section>
    </article>
  );
}

function PathRow({ platform, path }: { platform: string; path: string }) {
  return (
    <div className="flex items-start gap-3">
      <span
        className="text-[12px] font-medium shrink-0"
        style={{ color: "var(--foreground)", minWidth: 60 }}
      >
        {platform}
      </span>
      <code
        className="text-[12px] font-mono"
        style={{ color: "var(--muted)" }}
      >
        {path}
      </code>
    </div>
  );
}

function CodeBlock({ code, label }: { code: string; label?: string }) {
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
        className="flex items-center justify-between px-4 py-2"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}
      >
        {label ? (
          <span
            className="text-[12px] font-medium"
            style={{ color: "rgba(231, 229, 228, 0.4)" }}
          >
            {label}
          </span>
        ) : (
          <span />
        )}
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

const ENV_VARS = [
  {
    name: "CMK_STORAGE",
    description: "Storage mode: local or cloud",
    defaultValue: "local",
  },
  {
    name: "CMK_API_KEY",
    description: "Your CMK API key (cloud mode via self-hosted server)",
    defaultValue: "none",
  },
  {
    name: "CMK_PORT",
    description: "Server port",
    defaultValue: "7749",
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
