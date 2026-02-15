const PROBLEMS = [
  {
    title: "Claude forgets everything",
    description:
      "Every session starts from zero. Your preferences, your stack, your conventions.",
    color: "var(--gate-correction)",
  },
  {
    title: "Context windows expire",
    description:
      "The 200k window is big, but temporary. None of it persists.",
    color: "var(--gate-behavioral)",
  },
  {
    title: "You repeat yourself",
    description:
      "Retyping your setup instructions. Re-explaining your codebase. Again and again.",
    color: "var(--gate-epistemic)",
  },
];

export function ProblemCards() {
  return (
    <section className="max-w-4xl mx-auto px-6 py-20">
      <div className="space-y-4">
        {PROBLEMS.map((problem, i) => (
          <div
            key={i}
            className="rounded-[var(--radius)] p-6 pl-8"
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderLeft: `3px solid ${problem.color}`,
              boxShadow: "var(--shadow-xs)",
              animation: `drift-up 300ms ease ${i * 100}ms both`,
            }}
          >
            <h3
              className="text-[17px] font-semibold tracking-tight mb-1.5"
              style={{ color: "var(--foreground)" }}
            >
              {problem.title}
            </h3>
            <p
              className="text-[15px] leading-[1.6]"
              style={{ color: "var(--muted)" }}
            >
              {problem.description}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
