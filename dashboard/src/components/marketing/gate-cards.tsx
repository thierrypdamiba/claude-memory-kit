const GATES = [
  {
    name: "behavioral",
    color: "var(--gate-behavioral)",
    colorBg: "rgba(217, 119, 6, 0.1)",
    definition: "Preferences, habits, and workflow patterns.",
    example: '"I always use tabs over spaces."',
    scope: "user",
    decay: "slow",
  },
  {
    name: "relational",
    color: "var(--gate-relational)",
    colorBg: "rgba(37, 99, 235, 0.1)",
    definition: "People, teams, and social context.",
    example: '"Sarah is the lead on the auth service."',
    scope: "project",
    decay: "medium",
  },
  {
    name: "epistemic",
    color: "var(--gate-epistemic)",
    colorBg: "rgba(124, 58, 237, 0.1)",
    definition: "Facts, knowledge, and technical details.",
    example: '"Our API uses JWT with RS256 signing."',
    scope: "project",
    decay: "slow",
  },
  {
    name: "promissory",
    color: "var(--gate-promissory)",
    colorBg: "rgba(5, 150, 105, 0.1)",
    definition: "Commitments and agreed-upon plans.",
    example: '"We decided to migrate to Postgres next sprint."',
    scope: "project",
    decay: "fast",
  },
  {
    name: "correction",
    color: "var(--gate-correction)",
    colorBg: "rgba(220, 38, 38, 0.1)",
    definition: "Mistakes to avoid and corrections.",
    example: '"Don\'t use the legacy endpoint, it\'s deprecated."',
    scope: "global",
    decay: "medium",
  },
];

export function GateCards() {
  return (
    <section className="max-w-5xl mx-auto px-6 py-20">
      <h2
        className="text-[32px] font-normal tracking-tight mb-2"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        Five memory gates
      </h2>
      <p
        className="text-[15px] leading-[1.6] mb-10"
        style={{ color: "var(--muted)" }}
      >
        Every memory is classified through one of five gates, each with its own
        scope and decay behavior.
      </p>

      {/* Horizontal scroll container */}
      <div
        className="flex gap-4 overflow-x-auto pb-4"
        style={{
          scrollSnapType: "x mandatory",
          WebkitOverflowScrolling: "touch",
        }}
      >
        {GATES.map((gate, i) => (
          <div
            key={gate.name}
            className="flex-shrink-0 w-[260px] rounded-[var(--radius)] p-5 flex flex-col"
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              boxShadow: "var(--shadow-sm)",
              scrollSnapAlign: "start",
              animation: `drift-up 300ms ease ${i * 80}ms both`,
            }}
          >
            {/* Gate name + color dot */}
            <div className="flex items-center gap-2 mb-3">
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ background: gate.color }}
              />
              <span
                className="text-[15px] font-semibold capitalize tracking-tight"
                style={{ color: "var(--foreground)" }}
              >
                {gate.name}
              </span>
            </div>

            {/* Definition */}
            <p
              className="text-[13px] leading-[1.5] mb-3"
              style={{ color: "var(--muted)" }}
            >
              {gate.definition}
            </p>

            {/* Example quote */}
            <p
              className="text-[13px] leading-[1.5] mb-4 flex-1"
              style={{
                color: "var(--foreground)",
                fontStyle: "italic",
                fontFamily: "var(--font-serif)",
              }}
            >
              {gate.example}
            </p>

            {/* Metadata chips */}
            <div className="flex items-center gap-2">
              <span
                className="px-2 py-1 rounded-[4px] text-[11px] font-medium"
                style={{
                  background: gate.colorBg,
                  color: gate.color,
                }}
              >
                {gate.scope}
              </span>
              <span
                className="px-2 py-1 rounded-[4px] text-[11px] font-medium"
                style={{
                  background: "var(--warm-paper)",
                  color: "var(--muted)",
                }}
              >
                {gate.decay} decay
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
