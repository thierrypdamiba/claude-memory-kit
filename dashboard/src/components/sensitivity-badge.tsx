"use client";

const LEVEL_STYLES: Record<string, { bg: string; color: string; label: string }> = {
  safe: {
    bg: "var(--success)",
    color: "#fff",
    label: "safe",
  },
  sensitive: {
    bg: "var(--gate-behavioral)",
    color: "#fff",
    label: "sensitive",
  },
  critical: {
    bg: "var(--gate-correction)",
    color: "#fff",
    label: "critical",
  },
  unclassified: {
    bg: "var(--dust)",
    color: "#fff",
    label: "unclassified",
  },
};

export function SensitivityBadge({ level }: { level: string | null }) {
  const style = LEVEL_STYLES[level || "unclassified"] || LEVEL_STYLES.unclassified;

  return (
    <span
      className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium uppercase tracking-wider"
      style={{
        background: style.bg,
        color: style.color,
        fontSize: "10px",
        lineHeight: "14px",
      }}
    >
      {style.label}
    </span>
  );
}
