"use client";

import { useState, useCallback } from "react";
import Link from "next/link";

export default function DocsQuickstartPage() {
  return (
    <article style={{ animation: "drift-up 400ms ease both" }}>
      <h1
        className="text-[36px] font-normal tracking-tight mb-3"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        Quickstart
      </h1>
      <p
        className="text-[16px] leading-[1.65] mb-10 max-w-2xl"
        style={{ color: "var(--muted)" }}
      >
        One command. Claude remembers everything from now on.
      </p>

      {/* Cloud happy path */}
      <div className="space-y-10">
        <StepSection number={1} title="Sign up and get your API key">
          <p
            className="text-[14px] leading-[1.65] mb-4"
            style={{ color: "var(--muted)" }}
          >
            Create an account and copy your API key from the dashboard.
          </p>
          <Link
            href="/sign-up"
            className="inline-block px-5 py-2.5 rounded-[var(--radius)] text-[14px] font-medium"
            style={{
              background: "var(--foreground)",
              color: "var(--background)",
            }}
          >
            Sign up
          </Link>
        </StepSection>

        <StepSection number={2} title="Add to Claude">
          <TabSwitcher />
        </StepSection>
      </div>

      {/* Done */}
      <div
        className="mt-10 rounded-[var(--radius)] p-5"
        style={{
          background: "var(--warm-paper)",
          border: "1px solid var(--border-light)",
        }}
      >
        <p
          className="text-[15px] font-medium mb-3"
          style={{ color: "var(--foreground)" }}
        >
          That&apos;s it. Start chatting.
        </p>
        <p
          className="text-[13px] leading-[1.6] mb-4"
          style={{ color: "var(--muted)" }}
        >
          No local server. No Python. No dependencies. Memories are stored and
          recalled automatically:
        </p>
        <div className="space-y-2">
          <ExampleMessage role="user">
            I always use VS Code and prefer 2-space indentation.
          </ExampleMessage>
          <ExampleMessage role="note">
            Start a new session...
          </ExampleMessage>
          <ExampleMessage role="user">
            What editor do I use?
          </ExampleMessage>
          <ExampleMessage role="assistant">
            You use VS Code with 2-space indentation.
          </ExampleMessage>
        </div>
      </div>

      {/* Self-hosted / Local */}
      <div
        className="mt-10 rounded-[var(--radius)] p-5"
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
            Want to self-host or run fully local?
          </summary>
          <div className="mt-4 space-y-4">
            <p
              className="text-[13px] leading-[1.6]"
              style={{ color: "var(--muted)" }}
            >
              Install the CLI to run your own server. Local mode uses SQLite
              and fastembed on your machine. No account, no network calls.
            </p>
            <CodeBlock code={`pip install claude-memory-kit\ncmk init\ncmk serve --port 7749`} />
            <p
              className="text-[13px] leading-[1.6]"
              style={{ color: "var(--muted)" }}
            >
              Then add the MCP config manually. See the{" "}
              <Link
                href="/docs/mcp"
                style={{ color: "var(--accent)", textDecoration: "underline" }}
              >
                MCP configuration guide
              </Link>{" "}
              for details.
            </p>
          </div>
        </details>
      </div>

      {/* Next steps */}
      <div
        className="mt-12 pt-8"
        style={{ borderTop: "1px solid var(--border-light)" }}
      >
        <h2
          className="text-[20px] font-semibold tracking-tight mb-4"
          style={{ color: "var(--foreground)" }}
        >
          Next steps
        </h2>
        <div className="grid sm:grid-cols-2 gap-3">
          <NextLink href="/docs/mcp" title="MCP Configuration" desc="Manual setup and environment variables" />
          <NextLink href="/docs/api" title="API Reference" desc="Full HTTP API documentation" />
          <NextLink href="/docs/cli" title="CLI Reference" desc="All available CLI commands" />
          <NextLink href="/memory-model" title="Memory Model" desc="How gates, decay, and scoring work" />
        </div>
      </div>
    </article>
  );
}

function TabSwitcher() {
  const [tab, setTab] = useState<"code" | "desktop">("code");

  return (
    <div>
      <div className="flex gap-2 mb-4">
        {(["code", "desktop"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className="px-3 py-1.5 rounded-[var(--radius-sm)] text-[13px]"
            style={{
              background: tab === t ? "var(--surface-active)" : "var(--surface)",
              border: `1px solid ${tab === t ? "var(--accent)" : "var(--border-light)"}`,
              color: tab === t ? "var(--foreground)" : "var(--muted)",
              fontWeight: tab === t ? 500 : 400,
            }}
          >
            {t === "code" ? "Claude Code" : "Claude Desktop"}
          </button>
        ))}
      </div>

      {tab === "code" ? (
        <div>
          <p
            className="text-[14px] leading-[1.65] mb-4"
            style={{ color: "var(--muted)" }}
          >
            One command. Paste your API key and you&apos;re done.
          </p>
          <CodeBlock
            code={`claude mcp add cmk --url https://mcp.cmk.dev/v1 \\
  --header "Authorization: Bearer <your-api-key>"`}
          />
        </div>
      ) : (
        <div>
          <p
            className="text-[14px] leading-[1.65] mb-4"
            style={{ color: "var(--muted)" }}
          >
            Open Settings, then Developer, then Edit Config. Add this to your{" "}
            <code style={inlineCodeStyle}>claude_desktop_config.json</code>:
          </p>
          <CodeBlock
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
        </div>
      )}
    </div>
  );
}

function StepSection({
  number,
  title,
  children,
}: {
  number: number;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <span
          className="w-7 h-7 rounded-full flex items-center justify-center text-[13px] font-semibold"
          style={{
            background: "var(--foreground)",
            color: "var(--background)",
          }}
        >
          {number}
        </span>
        <h2
          className="text-[20px] font-semibold tracking-tight"
          style={{ color: "var(--foreground)" }}
        >
          {title}
        </h2>
      </div>
      {children}
    </div>
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

function ExampleMessage({
  role,
  children,
}: {
  role: "user" | "assistant" | "note";
  children: React.ReactNode;
}) {
  if (role === "note") {
    return (
      <p
        className="text-[12px] italic py-1"
        style={{ color: "var(--muted-light)" }}
      >
        {children}
      </p>
    );
  }
  return (
    <div className="flex items-start gap-2">
      <span
        className="text-[11px] font-medium uppercase shrink-0 mt-[2px]"
        style={{
          color: role === "user" ? "var(--muted)" : "var(--sage)",
        }}
      >
        {role === "user" ? "You" : "Claude"}
      </span>
      <span
        className="text-[13px] leading-[1.5]"
        style={{ color: "var(--foreground)" }}
      >
        {children}
      </span>
    </div>
  );
}

function NextLink({
  href,
  title,
  desc,
}: {
  href: string;
  title: string;
  desc: string;
}) {
  return (
    <Link
      href={href}
      className="block rounded-[var(--radius-sm)] p-4"
      style={{
        border: "1px solid var(--border)",
        background: "var(--surface)",
        transition: "border-color 140ms ease, box-shadow 140ms ease",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = "var(--muted-light)";
        e.currentTarget.style.boxShadow = "var(--shadow-sm)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "var(--border)";
        e.currentTarget.style.boxShadow = "none";
      }}
    >
      <p
        className="text-[14px] font-medium mb-0.5"
        style={{ color: "var(--foreground)" }}
      >
        {title} &rarr;
      </p>
      <p className="text-[12px]" style={{ color: "var(--muted)" }}>
        {desc}
      </p>
    </Link>
  );
}

const inlineCodeStyle: React.CSSProperties = {
  background: "var(--warm-paper)",
  padding: "1px 5px",
  borderRadius: 4,
  fontSize: "12px",
  fontFamily: "var(--font-mono)",
  color: "var(--foreground)",
};
