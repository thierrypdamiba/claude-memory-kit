"use client";

import { useEffect, useState, useCallback } from "react";
import { api, type Memory, type PrivacyStats } from "@/lib/api";
import { SensitivityBadge } from "@/components/sensitivity-badge";

type Filter = "flagged" | "sensitive" | "critical" | "unclassified";

export default function PrivatePage() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [stats, setStats] = useState<PrivacyStats | null>(null);
  const [filter, setFilter] = useState<Filter>("flagged");
  const [loading, setLoading] = useState(true);
  const [classifying, setClassifying] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [memRes, statsRes] = await Promise.all([
        api.privateMemories(filter),
        api.privacyStats(),
      ]);
      setMemories(memRes.memories);
      setStats(statsRes);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    setLoading(true);
    fetchData();
  }, [fetchData]);

  const handleClassifyAll = async () => {
    setClassifying(true);
    try {
      await api.classify();
      await fetchData();
    } catch {
      // ignore
    } finally {
      setClassifying(false);
    }
  };

  const handleMarkSafe = async (id: string) => {
    try {
      await api.reclassify(id, "safe");
      setMemories((prev) => prev.filter((m) => m.id !== id));
      setStats((s) => s ? { ...s, safe: s.safe + 1 } : s);
    } catch {
      // ignore
    }
  };

  const handleRedact = async (id: string) => {
    if (!confirm("This will permanently replace the memory content with [REDACTED]. Continue?")) return;
    try {
      await api.bulkPrivateAction([id], "redact");
      setMemories((prev) => prev.filter((m) => m.id !== id));
    } catch {
      // ignore
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Permanently delete this memory?")) return;
    try {
      await api.bulkPrivateAction([id], "delete");
      setMemories((prev) => prev.filter((m) => m.id !== id));
    } catch {
      // ignore
    }
  };

  const handleBulkAction = async (action: "delete" | "redact" | "reclassify") => {
    if (selected.size === 0) return;
    const ids = Array.from(selected);

    if (action === "delete") {
      if (!confirm(`Delete ${ids.length} memories?`)) return;
      await api.bulkPrivateAction(ids, "delete");
    } else if (action === "redact") {
      if (!confirm(`Redact ${ids.length} memories?`)) return;
      await api.bulkPrivateAction(ids, "redact");
    } else if (action === "reclassify") {
      await api.bulkPrivateAction(ids, "reclassify", "safe");
    }

    setSelected(new Set());
    await fetchData();
  };

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === memories.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(memories.map((m) => m.id)));
    }
  };

  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} />;

  const flaggedCount = (stats?.sensitive || 0) + (stats?.critical || 0);

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-[20px] font-semibold tracking-tight">Private Data</h2>
          <p className="text-[14px] mt-1" style={{ color: "var(--muted)" }}>
            {flaggedCount} flagged, {stats?.unclassified || 0} unclassified
          </p>
        </div>
        {stats && <StatsBar stats={stats} />}
      </div>

      {/* Actions bar */}
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={handleClassifyAll}
          disabled={classifying}
          className="px-3.5 py-2 rounded-[var(--radius-sm)] text-[13px] font-medium"
          style={{
            background: classifying ? "var(--surface-hover)" : "var(--accent)",
            color: classifying ? "var(--muted)" : "#fff",
            cursor: classifying ? "not-allowed" : "pointer",
          }}
        >
          {classifying ? "Classifying..." : "Classify All"}
        </button>

        {/* Filter tabs */}
        <div className="flex gap-1 ml-4">
          {(["flagged", "sensitive", "critical", "unclassified"] as Filter[]).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className="px-3 py-1.5 rounded-[var(--radius-sm)] text-[13px] capitalize"
              style={{
                background: filter === f ? "var(--surface-active)" : "transparent",
                color: filter === f ? "var(--foreground)" : "var(--muted)",
                fontWeight: filter === f ? 500 : 400,
              }}
            >
              {f}
            </button>
          ))}
        </div>

        {/* Bulk actions */}
        {selected.size > 0 && (
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-[13px]" style={{ color: "var(--muted)" }}>
              {selected.size} selected
            </span>
            <button
              onClick={() => handleBulkAction("reclassify")}
              className="px-2.5 py-1 rounded text-[12px]"
              style={{ background: "var(--surface-hover)", color: "var(--success)" }}
            >
              Mark Safe
            </button>
            <button
              onClick={() => handleBulkAction("redact")}
              className="px-2.5 py-1 rounded text-[12px]"
              style={{ background: "var(--surface-hover)", color: "var(--gate-behavioral)" }}
            >
              Redact
            </button>
            <button
              onClick={() => handleBulkAction("delete")}
              className="px-2.5 py-1 rounded text-[12px]"
              style={{ background: "var(--surface-hover)", color: "var(--gate-correction)" }}
            >
              Delete
            </button>
          </div>
        )}
      </div>

      {memories.length === 0 ? (
        <Empty filter={filter} />
      ) : (
        <div className="max-w-[720px]">
          {/* Select all */}
          <div className="flex items-center gap-2 mb-3 px-1">
            <input
              type="checkbox"
              checked={selected.size === memories.length && memories.length > 0}
              onChange={toggleSelectAll}
              className="rounded"
            />
            <span className="text-[12px]" style={{ color: "var(--dust)" }}>
              Select all
            </span>
          </div>

          {memories.map((m) => (
            <PrivateMemoryCard
              key={m.id}
              memory={m}
              isSelected={selected.has(m.id)}
              onToggle={() => toggleSelect(m.id)}
              onMarkSafe={() => handleMarkSafe(m.id)}
              onRedact={() => handleRedact(m.id)}
              onDelete={() => handleDelete(m.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}


function PrivateMemoryCard({
  memory,
  isSelected,
  onToggle,
  onMarkSafe,
  onRedact,
  onDelete,
}: {
  memory: Memory;
  isSelected: boolean;
  onToggle: () => void;
  onMarkSafe: () => void;
  onRedact: () => void;
  onDelete: () => void;
}) {
  const date = new Date(memory.created);

  return (
    <div
      className="rounded-[var(--radius)] p-5 mb-3 group"
      style={{
        background: "var(--warm-paper)",
        boxShadow: "var(--shadow-xs)",
        border: isSelected
          ? "1.5px solid var(--accent)"
          : "1px solid var(--border-light)",
      }}
    >
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onToggle}
          className="mt-1 rounded"
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <SensitivityBadge level={memory.sensitivity} />
            <span
              className="text-[12px] font-mono"
              style={{ color: "var(--dust)" }}
            >
              {memory.id.slice(0, 16)}
            </span>
            <span
              className="text-[12px] ml-auto tabular-nums"
              style={{ color: "var(--dust)" }}
            >
              {date.toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
              })}
            </span>
          </div>

          <p className="text-[14px] leading-[1.45] mb-2">{memory.content}</p>

          {memory.sensitivity_reason && (
            <p
              className="text-[13px] italic mb-3"
              style={{ color: "var(--muted)" }}
            >
              {memory.sensitivity_reason}
            </p>
          )}

          <div
            className="flex items-center gap-2 opacity-0 group-hover:opacity-100"
            style={{ transition: "opacity 140ms ease" }}
          >
            <button
              onClick={onMarkSafe}
              className="px-2.5 py-1 rounded text-[12px] font-medium"
              style={{
                background: "rgba(5, 150, 105, 0.1)",
                color: "var(--success)",
              }}
            >
              Mark Safe
            </button>
            <button
              onClick={onRedact}
              className="px-2.5 py-1 rounded text-[12px] font-medium"
              style={{
                background: "rgba(217, 119, 6, 0.1)",
                color: "var(--gate-behavioral)",
              }}
            >
              Redact
            </button>
            <button
              onClick={onDelete}
              className="px-2.5 py-1 rounded text-[12px] font-medium"
              style={{
                background: "rgba(220, 38, 38, 0.1)",
                color: "var(--gate-correction)",
              }}
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}


function StatsBar({ stats }: { stats: PrivacyStats }) {
  const total = stats.total || 1;
  const segments = [
    { key: "safe", count: stats.safe, color: "var(--success)" },
    { key: "sensitive", count: stats.sensitive, color: "var(--gate-behavioral)" },
    { key: "critical", count: stats.critical, color: "var(--gate-correction)" },
    { key: "unclassified", count: stats.unclassified, color: "var(--dust)" },
  ].filter((s) => s.count > 0);

  return (
    <div className="flex items-center gap-3">
      <div
        className="flex h-1.5 w-40 rounded-full overflow-hidden"
        style={{ background: "var(--warm-paper)" }}
      >
        {segments.map((s) => (
          <div
            key={s.key}
            style={{
              width: `${(s.count / total) * 100}%`,
              background: s.color,
            }}
          />
        ))}
      </div>
      <span
        className="text-[12px] tabular-nums"
        style={{ color: "var(--dust)" }}
      >
        {stats.total}
      </span>
    </div>
  );
}


function Loading() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="flex flex-col items-center gap-3">
        <div
          className="w-5 h-5 rounded-full border-2 animate-spin"
          style={{
            borderColor: "var(--border)",
            borderTopColor: "var(--accent)",
          }}
        />
        <p className="text-[14px]" style={{ color: "var(--muted)" }}>
          Loading privacy data...
        </p>
      </div>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="max-w-md mx-auto mt-24">
      <div
        className="rounded-[var(--radius)] p-6"
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border-light)",
          boxShadow: "var(--shadow-sm)",
        }}
      >
        <h3 className="text-[16px] font-semibold mb-2">
          Something went wrong
        </h3>
        <p className="text-[14px] mb-4" style={{ color: "var(--sage)" }}>
          {message}
        </p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 rounded-[var(--radius)] text-[14px] font-medium"
          style={{ background: "var(--accent)", color: "#fff" }}
        >
          Refresh
        </button>
      </div>
    </div>
  );
}

function Empty({ filter }: { filter: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <div
        className="w-10 h-10 rounded-full flex items-center justify-center text-lg"
        style={{ background: "var(--surface-hover)", color: "var(--success)" }}
      >
        &#10003;
      </div>
      <div className="text-center">
        <p
          className="text-[16px] font-medium"
          style={{ color: "var(--muted)", fontFamily: "var(--font-serif)" }}
        >
          {filter === "flagged"
            ? "No flagged memories"
            : `No ${filter} memories`}
        </p>
        <p className="text-[13px] mt-1" style={{ color: "var(--dust)" }}>
          {filter === "unclassified"
            ? 'Click "Classify All" to scan your memories with Opus.'
            : "All clear. Your memories look safe."}
        </p>
      </div>
    </div>
  );
}
