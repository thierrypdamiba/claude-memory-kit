"use client";

import { useState, useCallback } from "react";

const TABS = [
  {
    label: "Claude Code",
    language: "bash",
    code: `claude mcp add cmk --url https://mcp.cmk.dev/v1 \\
  --header "Authorization: Bearer <your-api-key>"`,
  },
  {
    label: "Claude Desktop",
    language: "json",
    code: `{
  "mcpServers": {
    "cmk": {
      "url": "https://mcp.cmk.dev/v1",
      "headers": {
        "Authorization": "Bearer <your-api-key>"
      }
    }
  }
}`,
  },
  {
    label: "API",
    language: "bash",
    code: `curl -X POST https://mcp.cmk.dev/v1/search \\
  -H "Authorization: Bearer <your-api-key>" \\
  -H "Content-Type: application/json" \\
  -d '{"query": "preferred database", "limit": 5}'`,
  },
];

export function TerminalTabs() {
  const [activeTab, setActiveTab] = useState(0);
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(TABS[activeTab].code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }, [activeTab]);

  return (
    <section className="max-w-4xl mx-auto px-6 py-20">
      <h2
        className="text-[32px] font-normal tracking-tight mb-2"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        Get started in seconds
      </h2>
      <p
        className="text-[15px] leading-[1.6] mb-10"
        style={{ color: "var(--muted)" }}
      >
        One command to install. Three ways to integrate.
      </p>

      {/* Terminal window */}
      <div
        className="rounded-[var(--radius-lg)] overflow-hidden"
        style={{
          background: "var(--code-bg)",
          boxShadow: "var(--shadow-md)",
        }}
      >
        {/* Tab bar */}
        <div
          className="flex items-center justify-between px-4"
          style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}
        >
          <div className="flex">
            {TABS.map((tab, i) => (
              <button
                key={tab.label}
                onClick={() => {
                  setActiveTab(i);
                  setCopied(false);
                }}
                className="px-4 py-3 text-[13px] font-medium"
                style={{
                  color:
                    activeTab === i
                      ? "var(--code-fg)"
                      : "rgba(231, 229, 228, 0.4)",
                  borderBottom:
                    activeTab === i
                      ? "2px solid var(--accent)"
                      : "2px solid transparent",
                  transition: "color 140ms ease, border-color 140ms ease",
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Copy button */}
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-[var(--radius-sm)] text-[12px] font-medium"
            style={{
              color: copied ? "var(--gate-promissory)" : "rgba(231, 229, 228, 0.5)",
              background: copied
                ? "rgba(5, 150, 105, 0.15)"
                : "rgba(255, 255, 255, 0.05)",
              transition: "all 140ms ease",
            }}
            onMouseEnter={(e) => {
              if (!copied) {
                e.currentTarget.style.background = "rgba(255, 255, 255, 0.1)";
              }
            }}
            onMouseLeave={(e) => {
              if (!copied) {
                e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)";
              }
            }}
          >
            {copied ? (
              <>
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                Copied
              </>
            ) : (
              <>
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
                </svg>
                Copy
              </>
            )}
          </button>
        </div>

        {/* Code area */}
        <div className="p-5 overflow-x-auto">
          <pre
            className="text-[13px] leading-[1.6] font-mono"
            style={{ color: "var(--code-fg)" }}
          >
            <code>{TABS[activeTab].code}</code>
          </pre>
        </div>
      </div>
    </section>
  );
}
