"use client";

interface Props {
  threshold: number;
  onThresholdChange: (value: number) => void;
  showLabels: boolean;
  onShowLabelsChange: (value: boolean) => void;
  viewMode: "graph" | "list";
  onViewModeChange: (value: "graph" | "list") => void;
}

export function GraphControls({
  threshold,
  onThresholdChange,
  showLabels,
  onShowLabelsChange,
  viewMode,
  onViewModeChange,
}: Props) {
  return (
    <div
      className="flex items-center gap-4 mb-4 px-4 py-3 rounded-[var(--radius)]"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border-light)",
        boxShadow: "var(--shadow-xs)",
      }}
    >
      {/* Threshold slider */}
      <div className="flex items-center gap-2">
        <label className="text-[12px] font-medium" style={{ color: "var(--sage)" }}>
          Similarity
        </label>
        <input
          type="range"
          min={0}
          max={100}
          value={threshold}
          onChange={(e) => onThresholdChange(Number(e.target.value))}
          className="w-24 h-1 accent-[var(--accent)]"
        />
        <span
          className="text-[12px] tabular-nums w-8"
          style={{ color: "var(--dust)" }}
        >
          {threshold}%
        </span>
      </div>

      <span className="w-px h-4" style={{ background: "var(--border)" }} />

      {/* Labels toggle */}
      <button
        onClick={() => onShowLabelsChange(!showLabels)}
        className="flex items-center gap-1.5 text-[12px] font-medium"
        style={{
          color: showLabels ? "var(--foreground)" : "var(--muted)",
        }}
      >
        <span
          className="w-3 h-3 rounded-sm border flex items-center justify-center text-[8px]"
          style={{
            borderColor: showLabels ? "var(--accent)" : "var(--border)",
            background: showLabels ? "var(--accent)" : "transparent",
            color: "#fff",
          }}
        >
          {showLabels ? "\u2713" : ""}
        </span>
        Labels
      </button>

      <span className="w-px h-4" style={{ background: "var(--border)" }} />

      {/* View mode */}
      <div className="flex gap-1">
        <button
          onClick={() => onViewModeChange("graph")}
          className="px-2 py-1 rounded-[4px] text-[12px] font-medium"
          style={{
            background:
              viewMode === "graph" ? "var(--surface-active)" : "transparent",
            color:
              viewMode === "graph" ? "var(--foreground)" : "var(--muted)",
          }}
        >
          Graph
        </button>
        <button
          onClick={() => onViewModeChange("list")}
          className="px-2 py-1 rounded-[4px] text-[12px] font-medium"
          style={{
            background:
              viewMode === "list" ? "var(--surface-active)" : "transparent",
            color:
              viewMode === "list" ? "var(--foreground)" : "var(--muted)",
          }}
        >
          List
        </button>
      </div>
    </div>
  );
}
