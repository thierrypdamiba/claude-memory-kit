export default function MemoryModelPage() {
  return (
    <div>
      {/* Hero */}
      <section
        className="max-w-4xl mx-auto px-6 pt-24 pb-16"
        style={{ animation: "drift-up 400ms ease both" }}
      >
        <h1
          className="text-[48px] md:text-[56px] font-normal tracking-tight leading-[1.08] mb-6"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          The memory model
        </h1>
        <p
          className="text-[18px] leading-[1.65] max-w-2xl"
          style={{ color: "var(--muted)" }}
        >
          Every piece of information that CMK stores passes through a
          classification pipeline. Five semantic gates determine what gets
          remembered, how long it persists, and how confidently it can be
          recalled.
        </p>
      </section>

      {/* Five Gates - Detailed */}
      <section className="max-w-5xl mx-auto px-6 py-16">
        <h2
          className="text-[32px] font-normal tracking-tight mb-2"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          Five semantic gates
        </h2>
        <p
          className="text-[15px] leading-[1.6] mb-10"
          style={{ color: "var(--muted)" }}
        >
          Each memory is routed through exactly one gate. The gate determines
          scope, default decay, and retrieval priority.
        </p>

        <div className="space-y-5">
          {GATES_DETAILED.map((gate, i) => (
            <div
              key={gate.name}
              className="rounded-[var(--radius)] p-6"
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderLeft: `3px solid ${gate.color}`,
                boxShadow: "var(--shadow-xs)",
                animation: `drift-up 300ms ease ${i * 80}ms both`,
              }}
            >
              <div className="flex items-start gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2.5 mb-2">
                    <span
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ background: gate.color }}
                    />
                    <h3
                      className="text-[17px] font-semibold tracking-tight capitalize"
                      style={{ color: "var(--foreground)" }}
                    >
                      {gate.name}
                    </h3>
                    <span
                      className="px-2 py-[2px] rounded-[4px] text-[11px] font-medium"
                      style={{ background: gate.colorBg, color: gate.color }}
                    >
                      {gate.scope}
                    </span>
                  </div>
                  <p
                    className="text-[14px] leading-[1.65] mb-3"
                    style={{ color: "var(--muted)" }}
                  >
                    {gate.longDescription}
                  </p>
                  <div
                    className="rounded-[var(--radius-sm)] px-4 py-3"
                    style={{
                      background: "var(--warm-paper)",
                      border: "1px solid var(--border-light)",
                    }}
                  >
                    <p
                      className="text-[13px] leading-[1.5]"
                      style={{
                        fontStyle: "italic",
                        fontFamily: "var(--font-serif)",
                        color: "var(--foreground)",
                      }}
                    >
                      {gate.example}
                    </p>
                  </div>
                </div>
                <div
                  className="hidden md:flex flex-col items-end gap-2 shrink-0"
                >
                  <span
                    className="px-2 py-1 rounded-[4px] text-[11px] font-medium"
                    style={{
                      background: "var(--warm-paper)",
                      color: "var(--muted)",
                    }}
                  >
                    {gate.defaultDecay} decay
                  </span>
                  <span
                    className="px-2 py-1 rounded-[4px] text-[11px] font-medium"
                    style={{
                      background: "var(--warm-paper)",
                      color: "var(--muted)",
                    }}
                  >
                    priority: {gate.priority}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Decay Classes */}
      <section className="max-w-4xl mx-auto px-6 py-16">
        <h2
          className="text-[32px] font-normal tracking-tight mb-2"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          Decay classes
        </h2>
        <p
          className="text-[15px] leading-[1.6] mb-10"
          style={{ color: "var(--muted)" }}
        >
          Memories do not live forever by default. Each is assigned a decay
          class that determines how quickly its confidence degrades over time.
        </p>

        <div className="grid md:grid-cols-2 gap-5">
          {DECAY_CLASSES.map((dc, i) => (
            <div
              key={dc.name}
              className="rounded-[var(--radius)] p-5"
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                boxShadow: "var(--shadow-xs)",
                animation: `drift-up 300ms ease ${i * 80}ms both`,
              }}
            >
              <div className="flex items-center gap-2.5 mb-3">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ background: dc.color }}
                />
                <h3
                  className="text-[15px] font-semibold tracking-tight capitalize"
                  style={{ color: "var(--foreground)" }}
                >
                  {dc.name}
                </h3>
                <span
                  className="text-[12px] font-mono"
                  style={{ color: "var(--muted-light)" }}
                >
                  {dc.halfLife}
                </span>
              </div>
              <p
                className="text-[13px] leading-[1.55] mb-3"
                style={{ color: "var(--muted)" }}
              >
                {dc.description}
              </p>
              <p
                className="text-[12px] leading-[1.5]"
                style={{ color: "var(--muted-light)" }}
              >
                Examples: {dc.examples}
              </p>
            </div>
          ))}
        </div>

        <div
          className="mt-6 flex items-center justify-center gap-2 py-3"
          style={{ color: "var(--muted)" }}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span className="text-[13px]">
            Pinned memories bypass decay entirely. They persist until manually
            unpinned.
          </span>
        </div>
      </section>

      {/* Confidence Scoring */}
      <section className="max-w-4xl mx-auto px-6 py-16">
        <h2
          className="text-[32px] font-normal tracking-tight mb-2"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          Confidence scoring
        </h2>
        <p
          className="text-[15px] leading-[1.6] mb-10"
          style={{ color: "var(--muted)" }}
        >
          Every memory carries a confidence score between 0 and 100. This
          score determines recall priority and is influenced by several
          factors.
        </p>

        <div
          className="rounded-[var(--radius-lg)] overflow-hidden"
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
                  className="text-left px-5 py-3.5 text-[13px] font-semibold"
                  style={{ color: "var(--foreground)" }}
                >
                  Factor
                </th>
                <th
                  className="text-left px-5 py-3.5 text-[13px] font-semibold"
                  style={{ color: "var(--foreground)" }}
                >
                  Effect
                </th>
                <th
                  className="text-left px-5 py-3.5 text-[13px] font-semibold"
                  style={{ color: "var(--foreground)" }}
                >
                  Impact
                </th>
              </tr>
            </thead>
            <tbody>
              {CONFIDENCE_FACTORS.map((factor, i) => (
                <tr
                  key={i}
                  style={{
                    borderBottom:
                      i < CONFIDENCE_FACTORS.length - 1
                        ? "1px solid var(--border-light)"
                        : "none",
                    background:
                      i % 2 === 0 ? "var(--surface)" : "var(--background)",
                  }}
                >
                  <td
                    className="px-5 py-3 text-[13px] font-medium"
                    style={{ color: "var(--foreground)" }}
                  >
                    {factor.name}
                  </td>
                  <td
                    className="px-5 py-3 text-[13px]"
                    style={{ color: "var(--muted)" }}
                  >
                    {factor.effect}
                  </td>
                  <td className="px-5 py-3 text-[13px]">
                    <span
                      className="px-2 py-[2px] rounded-[4px] text-[11px] font-medium"
                      style={{
                        background:
                          factor.direction === "up"
                            ? "rgba(5, 150, 105, 0.1)"
                            : "rgba(220, 38, 38, 0.1)",
                        color:
                          factor.direction === "up"
                            ? "var(--success)"
                            : "var(--gate-correction)",
                      }}
                    >
                      {factor.impact}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Storage Architecture */}
      <section className="max-w-4xl mx-auto px-6 py-16 pb-24">
        <h2
          className="text-[32px] font-normal tracking-tight mb-2"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          Storage architecture
        </h2>
        <p
          className="text-[15px] leading-[1.6] mb-10"
          style={{ color: "var(--muted)" }}
        >
          CMK uses a dual-store design. Structured metadata lives in SQLite.
          Semantic representations live in a vector store.
        </p>

        <div className="grid md:grid-cols-2 gap-5">
          {/* SQLite */}
          <div
            className="rounded-[var(--radius)] p-6"
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderTop: "3px solid var(--gate-behavioral)",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            <div className="flex items-center gap-2.5 mb-4">
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ background: "var(--gate-behavioral)" }}
              />
              <h3
                className="text-[17px] font-semibold tracking-tight"
                style={{ color: "var(--foreground)" }}
              >
                SQLite (metadata)
              </h3>
            </div>
            <p
              className="text-[14px] leading-[1.6] mb-5"
              style={{ color: "var(--muted)" }}
            >
              Stores memory records, identity documents, gate classifications,
              confidence scores, timestamps, and decay state. Single file,
              zero configuration.
            </p>
            <div className="space-y-2">
              <MetaRow label="Location" value="~/.cmk/memories.db" />
              <MetaRow label="Schema" value="memories, identity, api_keys" />
              <MetaRow label="Migrations" value="auto on startup" />
              <MetaRow label="Backup" value="standard file copy" />
            </div>
          </div>

          {/* Vectors */}
          <div
            className="rounded-[var(--radius)] p-6"
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderTop: "3px solid var(--gate-epistemic)",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            <div className="flex items-center gap-2.5 mb-4">
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ background: "var(--gate-epistemic)" }}
              />
              <h3
                className="text-[17px] font-semibold tracking-tight"
                style={{ color: "var(--foreground)" }}
              >
                Vector store (embeddings)
              </h3>
            </div>
            <p
              className="text-[14px] leading-[1.6] mb-5"
              style={{ color: "var(--muted)" }}
            >
              Stores embedding vectors for semantic search. In local mode,
              uses fastembed with on-disk storage. In cloud mode, uses Qdrant
              Cloud with Jina embeddings.
            </p>
            <div className="space-y-2">
              <MetaRow label="Local engine" value="fastembed" />
              <MetaRow label="Cloud engine" value="Qdrant Cloud + Jina" />
              <MetaRow label="Dimensions" value="384 (local) / 768 (cloud)" />
              <MetaRow label="Search" value="cosine similarity + keyword" />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start gap-2">
      <span
        className="text-[12px] font-medium shrink-0"
        style={{ color: "var(--muted-light)", minWidth: 80 }}
      >
        {label}
      </span>
      <span
        className="text-[12px] font-mono"
        style={{ color: "var(--muted)" }}
      >
        {value}
      </span>
    </div>
  );
}

const GATES_DETAILED = [
  {
    name: "behavioral",
    color: "var(--gate-behavioral)",
    colorBg: "rgba(217, 119, 6, 0.1)",
    scope: "user",
    defaultDecay: "slow",
    priority: "high",
    longDescription:
      "Captures preferences, habits, and workflow patterns. These are things you do consistently: your editor choice, preferred languages, formatting style, testing approach. Behavioral memories form the backbone of your identity document and tend to be stable over time.",
    example:
      '"I always use 2-space indentation. I prefer functional components over class components. I run tests with pytest and use fixtures heavily."',
  },
  {
    name: "relational",
    color: "var(--gate-relational)",
    colorBg: "rgba(37, 99, 235, 0.1)",
    scope: "project",
    defaultDecay: "medium",
    priority: "medium",
    longDescription:
      "Tracks people, teams, and social context around your work. Who owns what service, who reviews which PRs, team structure, and reporting lines. Relational memories are scoped to projects because team structure varies across codebases.",
    example:
      '"Sarah leads the auth service. Marcus handles the data pipeline. The design team uses Figma and ships weekly."',
  },
  {
    name: "epistemic",
    color: "var(--gate-epistemic)",
    colorBg: "rgba(124, 58, 237, 0.1)",
    scope: "project",
    defaultDecay: "slow",
    priority: "high",
    longDescription:
      "Stores facts, knowledge, and technical details about your systems. Architecture decisions, API contracts, database schemas, deployment configurations. Epistemic memories are the factual foundation that Claude references when answering technical questions.",
    example:
      '"Our API uses JWT with RS256 signing. The user table has a composite index on (org_id, email). We deploy to AWS us-east-1."',
  },
  {
    name: "promissory",
    color: "var(--gate-promissory)",
    colorBg: "rgba(5, 150, 105, 0.1)",
    scope: "project",
    defaultDecay: "fast",
    priority: "high",
    longDescription:
      "Records commitments, plans, and agreed-upon future actions. These naturally expire faster because plans change. When a promissory memory decays, it signals that the commitment may need to be revisited or confirmed.",
    example:
      '"We decided to migrate to Postgres next sprint. The API v2 launch is scheduled for March. I promised to refactor the auth middleware before Friday."',
  },
  {
    name: "correction",
    color: "var(--gate-correction)",
    colorBg: "rgba(220, 38, 38, 0.1)",
    scope: "global",
    defaultDecay: "medium",
    priority: "very high",
    longDescription:
      "Captures mistakes to avoid and explicit corrections. When you tell Claude it got something wrong, that correction is stored globally so the same mistake is not repeated in any project. Corrections have the highest retrieval priority.",
    example:
      '"Do not use the legacy /v1/users endpoint. The config key is database_url, not db_url. Never commit .env files to the repo."',
  },
];

const DECAY_CLASSES = [
  {
    name: "ephemeral",
    color: "var(--gate-correction)",
    halfLife: "~24h",
    description:
      "Very short-lived memories that expire within a day. Used for transient context like current debugging sessions, temporary workarounds, or in-progress tasks that will be resolved shortly.",
    examples: "debugging notes, temporary workarounds, WIP context",
  },
  {
    name: "session",
    color: "var(--gate-behavioral)",
    halfLife: "~7d",
    description:
      "Memories that persist across a few sessions but fade within a week. Useful for short-term project context, sprint-level planning, or information that is relevant for a limited period.",
    examples: "sprint goals, short-term decisions, meeting follow-ups",
  },
  {
    name: "durable",
    color: "var(--gate-relational)",
    halfLife: "~90d",
    description:
      "Long-lived memories that persist for months. Most epistemic and behavioral memories fall into this class. They represent stable knowledge that changes infrequently.",
    examples: "tech stack choices, coding preferences, team structure",
  },
  {
    name: "permanent",
    color: "var(--gate-promissory)",
    halfLife: "never",
    description:
      "Memories that never decay. Reserved for pinned memories and core identity facts. Only assigned manually via the pin endpoint or when a memory is marked as critical.",
    examples: "pinned corrections, core identity facts, critical preferences",
  },
];

const CONFIDENCE_FACTORS = [
  {
    name: "Initial classification",
    effect: "Gate classifier assigns a base confidence based on signal clarity",
    impact: "60-95",
    direction: "up",
  },
  {
    name: "Repetition",
    effect: "Same information mentioned multiple times increases confidence",
    impact: "+5 per mention",
    direction: "up",
  },
  {
    name: "Recency",
    effect: "More recent memories get a recency boost during retrieval",
    impact: "+10 max",
    direction: "up",
  },
  {
    name: "Decay",
    effect: "Confidence decreases over time based on decay class",
    impact: "-varies",
    direction: "down",
  },
  {
    name: "Contradiction",
    effect: "New information that contradicts an existing memory lowers the older one",
    impact: "-20 to -50",
    direction: "down",
  },
  {
    name: "Pinning",
    effect: "Pinned memories are locked at their current confidence",
    impact: "locked",
    direction: "up",
  },
];
