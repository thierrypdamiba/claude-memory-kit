export function RecallProof() {
  return (
    <section id="recall-proof" className="max-w-4xl mx-auto px-6 py-20">
      <h2
        className="text-[32px] font-normal tracking-tight mb-2"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        Recall in action
      </h2>
      <p
        className="text-[15px] leading-[1.6] mb-10"
        style={{ color: "var(--muted)" }}
      >
        Ask a question. Claude pulls from stored memories and cites its sources.
      </p>

      {/* Two-column layout */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Left: User query */}
        <div
          className="rounded-[var(--radius)] p-6"
          style={{
            background: "var(--foreground)",
            color: "var(--background)",
            boxShadow: "var(--shadow-md)",
          }}
        >
          <p
            className="text-[11px] font-medium uppercase tracking-wider mb-3"
            style={{ color: "var(--muted-light)" }}
          >
            Your query
          </p>
          <p className="text-[16px] leading-[1.5]">
            What&apos;s my preferred database for new projects?
          </p>
        </div>

        {/* Right: Claude answer */}
        <div
          className="rounded-[var(--radius)] p-6"
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <p
            className="text-[11px] font-medium uppercase tracking-wider mb-3"
            style={{ color: "var(--sage)" }}
          >
            Claude&apos;s response
          </p>
          <p className="text-[15px] leading-[1.7]">
            Based on your previous conversations, you prefer{" "}
            <InlineMemory gate="behavioral" text="PostgreSQL" /> for most
            projects. You mentioned that{" "}
            <InlineMemory gate="epistemic" text="your team standardized on Postgres 16" />{" "}
            after evaluating alternatives. For quick prototypes, you sometimes
            reach for{" "}
            <InlineMemory gate="behavioral" text="SQLite" /> instead.
          </p>
        </div>
      </div>

      {/* Recall trace */}
      <div
        className="mt-6 rounded-[var(--radius)] p-5"
        style={{
          background: "var(--warm-paper)",
          border: "1px solid var(--border-light)",
        }}
      >
        <p
          className="text-[11px] font-medium uppercase tracking-wider mb-3"
          style={{ color: "var(--sage)" }}
        >
          Recall trace
        </p>
        <div className="space-y-2.5">
          <TraceRow
            gate="behavioral"
            score={94}
            content="User prefers PostgreSQL for production databases."
            source="vector"
          />
          <TraceRow
            gate="epistemic"
            score={87}
            content="Team standardized on Postgres 16 after evaluating CockroachDB and PlanetScale."
            source="vector"
          />
          <TraceRow
            gate="behavioral"
            score={72}
            content="Uses SQLite for prototypes and local-first apps."
            source="keyword"
          />
        </div>
      </div>
    </section>
  );
}

function InlineMemory({ gate, text }: { gate: string; text: string }) {
  const colors: Record<string, { bg: string; fg: string }> = {
    behavioral: {
      bg: "rgba(217, 119, 6, 0.12)",
      fg: "var(--gate-behavioral)",
    },
    relational: {
      bg: "rgba(37, 99, 235, 0.12)",
      fg: "var(--gate-relational)",
    },
    epistemic: {
      bg: "rgba(124, 58, 237, 0.12)",
      fg: "var(--gate-epistemic)",
    },
    promissory: {
      bg: "rgba(5, 150, 105, 0.12)",
      fg: "var(--gate-promissory)",
    },
    correction: {
      bg: "rgba(220, 38, 38, 0.12)",
      fg: "var(--gate-correction)",
    },
  };

  const style = colors[gate] || { bg: "var(--warm-paper)", fg: "var(--muted)" };

  return (
    <span
      className="inline-block px-1.5 py-0.5 rounded-[4px] text-[14px] font-medium"
      style={{ background: style.bg, color: style.fg }}
    >
      {text}
    </span>
  );
}

function TraceRow({
  gate,
  score,
  content,
  source,
}: {
  gate: string;
  score: number;
  content: string;
  source: string;
}) {
  const colors: Record<string, { bg: string; fg: string }> = {
    behavioral: {
      bg: "rgba(217, 119, 6, 0.1)",
      fg: "var(--gate-behavioral)",
    },
    epistemic: {
      bg: "rgba(124, 58, 237, 0.1)",
      fg: "var(--gate-epistemic)",
    },
    relational: {
      bg: "rgba(37, 99, 235, 0.1)",
      fg: "var(--gate-relational)",
    },
    promissory: {
      bg: "rgba(5, 150, 105, 0.1)",
      fg: "var(--gate-promissory)",
    },
    correction: {
      bg: "rgba(220, 38, 38, 0.1)",
      fg: "var(--gate-correction)",
    },
  };

  const style = colors[gate] || { bg: "var(--warm-paper)", fg: "var(--muted)" };

  return (
    <div
      className="flex items-center gap-3 px-3 py-2 rounded-[var(--radius-sm)]"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border-light)",
      }}
    >
      <span
        className="px-2 py-[2px] rounded-[4px] text-[11px] font-medium capitalize shrink-0"
        style={{ background: style.bg, color: style.fg }}
      >
        {gate}
      </span>
      <p
        className="text-[13px] leading-[1.4] flex-1 truncate"
        style={{ color: "var(--foreground)" }}
      >
        {content}
      </p>
      <span
        className="text-[11px] font-mono shrink-0"
        style={{ color: "var(--muted-light)" }}
      >
        {source}
      </span>
      <span
        className="text-[12px] font-medium tabular-nums shrink-0"
        style={{
          color:
            score > 80
              ? "var(--success)"
              : score > 50
                ? "var(--gate-behavioral)"
                : "var(--muted)",
        }}
      >
        {score}%
      </span>
    </div>
  );
}
