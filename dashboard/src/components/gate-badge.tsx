const GATE_STYLES: Record<string, { bg: string; fg: string }> = {
  behavioral: { bg: "rgba(217, 119, 6, 0.1)", fg: "var(--gate-behavioral)" },
  relational: { bg: "rgba(37, 99, 235, 0.1)", fg: "var(--gate-relational)" },
  epistemic: { bg: "rgba(124, 58, 237, 0.1)", fg: "var(--gate-epistemic)" },
  promissory: { bg: "rgba(5, 150, 105, 0.1)", fg: "var(--gate-promissory)" },
  correction: { bg: "rgba(220, 38, 38, 0.1)", fg: "var(--gate-correction)" },
};

export function GateBadge({ gate }: { gate: string }) {
  const style = GATE_STYLES[gate] || { bg: "var(--surface-hover)", fg: "var(--muted)" };
  return (
    <span
      className="inline-flex items-center px-2 py-[3px] rounded-[5px] text-[12px] font-medium capitalize"
      style={{ background: style.bg, color: style.fg }}
    >
      {gate}
    </span>
  );
}
