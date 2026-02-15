"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api, type Memory } from "@/lib/api";
import { MemoryCard } from "@/components/memory-card";

const GATES = ["behavioral", "relational", "epistemic", "promissory", "correction"];
const TIME_RANGES = [
  { label: "24h", days: 1 },
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
  { label: "All", days: 0 },
];
const SORT_OPTIONS = ["relevance", "recency"] as const;

function SearchContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";

  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  // Filters
  const [activeGates, setActiveGates] = useState<Set<string>>(new Set());
  const [timeRange, setTimeRange] = useState(0);
  const [sort, setSort] = useState<"relevance" | "recency">("relevance");

  useEffect(() => {
    if (initialQuery) {
      doSearch(initialQuery);
    }
  }, [initialQuery]);

  const doSearch = async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const [searchRes, memRes] = await Promise.all([
        api.search(q),
        api.memories(200),
      ]);
      // Use memories list as our searchable pool
      // Filter by query match (basic client-side matching)
      const lower = q.toLowerCase();
      const matched = memRes.memories.filter(
        (m) =>
          m.content.toLowerCase().includes(lower) ||
          (m.person && m.person.toLowerCase().includes(lower)) ||
          (m.project && m.project.toLowerCase().includes(lower))
      );
      setResults(matched.length > 0 ? matched : memRes.memories.slice(0, 20));
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    doSearch(query);
  };

  // Apply client-side filters
  const filtered = results.filter((m) => {
    if (activeGates.size > 0 && !activeGates.has(m.gate)) return false;
    if (timeRange > 0) {
      const cutoff = Date.now() - timeRange * 24 * 60 * 60 * 1000;
      if (new Date(m.created).getTime() < cutoff) return false;
    }
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    if (sort === "recency") {
      return new Date(b.created).getTime() - new Date(a.created).getTime();
    }
    return 0; // relevance = default order from search
  });

  const toggleGate = (gate: string) => {
    setActiveGates((prev) => {
      const next = new Set(prev);
      if (next.has(gate)) next.delete(gate);
      else next.add(gate);
      return next;
    });
  };

  return (
    <div>
      <h2 className="text-[20px] font-semibold tracking-tight mb-1">Search</h2>
      <p className="text-[14px] mb-6" style={{ color: "var(--muted)" }}>
        Query your memories by keyword, concept, or natural language.
      </p>

      <form onSubmit={handleSearch} className="max-w-2xl mb-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="What are you looking for?"
            className="flex-1 px-4 py-2.5 rounded-[var(--radius)] text-[14px] outline-none"
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              color: "var(--foreground)",
              boxShadow: "var(--shadow-xs)",
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = "var(--accent)";
              e.currentTarget.style.boxShadow = "0 0 0 3px rgba(192, 86, 33, 0.06)";
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = "var(--border)";
              e.currentTarget.style.boxShadow = "var(--shadow-xs)";
            }}
          />
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2.5 rounded-[var(--radius)] text-[14px] font-medium"
            style={{
              background: "var(--accent)",
              color: "white",
              opacity: loading ? 0.6 : 1,
            }}
            onMouseEnter={(e) => {
              if (!loading) e.currentTarget.style.background = "var(--accent-hover)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "var(--accent)";
            }}
          >
            {loading ? "..." : "Search"}
          </button>
        </div>
      </form>

      {/* Filter chips */}
      {searched && (
        <div className="max-w-2xl mb-6 flex flex-wrap items-center gap-2">
          {/* Gate toggles */}
          {GATES.map((gate) => (
            <button
              key={gate}
              onClick={() => toggleGate(gate)}
              className="px-2.5 py-1 rounded-full text-[12px] font-medium capitalize"
              style={{
                background: activeGates.has(gate)
                  ? `var(--gate-${gate})`
                  : "var(--warm-paper)",
                color: activeGates.has(gate) ? "#fff" : "var(--muted)",
                border: `1px solid ${
                  activeGates.has(gate)
                    ? `var(--gate-${gate})`
                    : "var(--border-light)"
                }`,
              }}
            >
              {gate}
            </button>
          ))}

          <span className="w-px h-4 mx-1" style={{ background: "var(--border)" }} />

          {/* Time range */}
          {TIME_RANGES.map((tr) => (
            <button
              key={tr.label}
              onClick={() => setTimeRange(tr.days)}
              className="px-2.5 py-1 rounded-full text-[12px] font-medium"
              style={{
                background:
                  timeRange === tr.days
                    ? "var(--surface-active)"
                    : "var(--warm-paper)",
                color:
                  timeRange === tr.days
                    ? "var(--foreground)"
                    : "var(--muted)",
                border: `1px solid ${
                  timeRange === tr.days
                    ? "var(--border)"
                    : "var(--border-light)"
                }`,
              }}
            >
              {tr.label}
            </button>
          ))}

          <span className="w-px h-4 mx-1" style={{ background: "var(--border)" }} />

          {/* Sort */}
          {SORT_OPTIONS.map((s) => (
            <button
              key={s}
              onClick={() => setSort(s)}
              className="px-2.5 py-1 rounded-full text-[12px] font-medium capitalize"
              style={{
                background:
                  sort === s ? "var(--surface-active)" : "var(--warm-paper)",
                color:
                  sort === s ? "var(--foreground)" : "var(--muted)",
                border: `1px solid ${
                  sort === s ? "var(--border)" : "var(--border-light)"
                }`,
              }}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Results */}
      {searched && !loading && (
        <div className="max-w-2xl">
          <p className="text-[13px] mb-3" style={{ color: "var(--dust)" }}>
            {sorted.length} result{sorted.length !== 1 ? "s" : ""}
          </p>
          {sorted.length === 0 ? (
            <p className="text-[14px] py-8 text-center" style={{ color: "var(--muted)" }}>
              No matching memories found.
            </p>
          ) : (
            sorted.map((m) => (
              <MemoryCard key={m.id} memory={m} />
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-64">
      <div className="w-5 h-5 rounded-full border-2 animate-spin"
        style={{ borderColor: "var(--border)", borderTopColor: "var(--accent)" }} />
    </div>}>
      <SearchContent />
    </Suspense>
  );
}
