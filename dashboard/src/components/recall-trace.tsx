import { GateBadge } from "./gate-badge";

interface TraceResult {
  memory: {
    id: string;
    content: string;
    gate: string;
    person?: string | null;
    project?: string | null;
  };
  score: number;
  source: string;
  match_info?: string;
}

interface Props {
  results: TraceResult[];
}

export function RecallTrace({ results }: Props) {
  if (results.length === 0) return null;

  return (
    <div className="space-y-2">
      <p
        className="text-[12px] font-medium uppercase tracking-wider"
        style={{ color: "var(--sage)" }}
      >
        Recall trace
      </p>
      {results.map((r, i) => (
        <div
          key={r.memory.id}
          className="rounded-[var(--radius-sm)] p-3"
          style={{
            background: "var(--warm-paper)",
            border: "1px solid var(--border-light)",
            animation: `drift-up 140ms ease ${i * 60}ms both`,
          }}
        >
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-2">
              <GateBadge gate={r.memory.gate} />
              <span
                className="text-[11px] font-mono"
                style={{ color: "var(--dust)" }}
              >
                {r.source}
              </span>
            </div>
            <span
              className="text-[12px] tabular-nums font-medium"
              style={{
                color:
                  r.score > 0.8
                    ? "var(--success)"
                    : r.score > 0.5
                      ? "var(--gate-behavioral)"
                      : "var(--muted)",
              }}
            >
              {(r.score * 100).toFixed(0)}%
            </span>
          </div>
          <p className="text-[13px] leading-[1.4] line-clamp-2">
            {r.memory.content}
          </p>
          {r.match_info && (
            <p
              className="text-[11px] mt-1 font-mono"
              style={{ color: "var(--dust)" }}
            >
              {r.match_info}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
