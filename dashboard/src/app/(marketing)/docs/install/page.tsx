"use client";

import { useState, useCallback } from "react";

export default function DocsInstallPage() {
  return (
    <article style={{ animation: "drift-up 400ms ease both" }}>
      <h1
        className="text-[36px] font-normal tracking-tight mb-3"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        Installation
      </h1>
      <p
        className="text-[16px] leading-[1.65] mb-10 max-w-2xl"
        style={{ color: "var(--muted)" }}
      >
        Install CMK and run setup. Two commands to get started.
      </p>

      {/* Quick install */}
      <section className="mb-10">
        <h2
          className="text-[20px] font-semibold tracking-tight mb-4"
          style={{ color: "var(--foreground)" }}
        >
          Install
        </h2>
        <CodeBlock code="pip install claude-memory-kit" />
        <p
          className="text-[13px] mt-3"
          style={{ color: "var(--muted-light)" }}
        >
          Requires Python 3.10+. Works on macOS, Linux, and Windows (WSL
          recommended).
        </p>
      </section>

      {/* Setup */}
      <section className="mb-10">
        <h2
          className="text-[20px] font-semibold tracking-tight mb-4"
          style={{ color: "var(--foreground)" }}
        >
          Setup
        </h2>
        <p
          className="text-[14px] leading-[1.65] mb-4"
          style={{ color: "var(--muted)" }}
        >
          Run setup to connect your account and auto-configure Claude. This
          handles MCP configuration, API key setup, and client detection.
        </p>
        <CodeBlock code="cmk setup" />
        <p
          className="text-[13px] mt-3"
          style={{ color: "var(--muted-light)" }}
        >
          Cloud mode is the default. We handle the vector database and
          embeddings. You just need your CMK account.
        </p>
      </section>

      {/* Alternative install methods */}
      <section className="mb-10">
        <h2
          className="text-[20px] font-semibold tracking-tight mb-4"
          style={{ color: "var(--foreground)" }}
        >
          Alternative install methods
        </h2>

        <div className="space-y-6">
          <div>
            <h3
              className="text-[15px] font-medium mb-2"
              style={{ color: "var(--foreground)" }}
            >
              uv (faster installs)
            </h3>
            <CodeBlock code="uv pip install claude-memory-kit" />
          </div>

          <div>
            <h3
              className="text-[15px] font-medium mb-2"
              style={{ color: "var(--foreground)" }}
            >
              From source
            </h3>
            <CodeBlock
              code={`git clone https://github.com/thierrydamiba/claude-memory.git
cd claude-memory
uv pip install -e .`}
            />
          </div>
        </div>
      </section>

      {/* Verify */}
      <section className="mb-10">
        <h2
          className="text-[20px] font-semibold tracking-tight mb-4"
          style={{ color: "var(--foreground)" }}
        >
          Verify installation
        </h2>
        <CodeBlock code="cmk --version" />
      </section>

      {/* Local mode */}
      <section>
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
              Local mode (advanced)
            </summary>
            <div className="mt-4 space-y-3">
              <p
                className="text-[13px] leading-[1.6]"
                style={{ color: "var(--muted)" }}
              >
                Skip cloud setup entirely. Local mode uses SQLite for storage
                and fastembed for vectors. Everything runs on your machine with
                zero network calls. No account needed.
              </p>
              <CodeBlock code={`cmk init\ncmk serve --port 7749`} />
              <p
                className="text-[13px]"
                style={{ color: "var(--muted-light)" }}
              >
                You will need to manually add the MCP config to your Claude
                client. See the MCP configuration docs.
              </p>
            </div>
          </details>
        </div>
      </section>
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
