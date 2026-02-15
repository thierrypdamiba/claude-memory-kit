"use client";

import { useEffect, useState } from "react";
import { api, type Stats } from "@/lib/api";
import { IdentitySection } from "@/components/identity-section";

interface ParsedSection {
  title: string;
  content: string;
  gate?: string;
}

function parseIdentitySections(text: string): ParsedSection[] {
  const lines = text.split("\n");
  const sections: ParsedSection[] = [];
  let current: ParsedSection | null = null;

  const gateMap: Record<string, string> = {
    preferences: "behavioral",
    habits: "behavioral",
    behavioral: "behavioral",
    relationships: "relational",
    people: "relational",
    relational: "relational",
    knowledge: "epistemic",
    learnings: "epistemic",
    epistemic: "epistemic",
    commitments: "promissory",
    promises: "promissory",
    promissory: "promissory",
    corrections: "correction",
    correction: "correction",
  };

  for (const line of lines) {
    const headerMatch = line.match(/^#{1,3}\s+(.+)/);
    if (headerMatch) {
      if (current) sections.push(current);
      const title = headerMatch[1].trim();
      const lower = title.toLowerCase();
      const gate = Object.entries(gateMap).find(([k]) =>
        lower.includes(k)
      )?.[1];
      current = { title, content: "", gate };
    } else if (current) {
      current.content += (current.content ? "\n" : "") + line;
    } else if (line.trim()) {
      current = { title: "Overview", content: line };
    }
  }
  if (current) sections.push(current);

  // Trim content
  return sections.map((s) => ({ ...s, content: s.content.trim() })).filter((s) => s.content);
}

export default function IdentityPage() {
  const [identity, setIdentity] = useState<string | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [reflecting, setReflecting] = useState(false);
  const [reflectResult, setReflectResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.identity(), api.stats()])
      .then(([idRes, statsRes]) => {
        setIdentity(idRes.identity);
        setStats(statsRes);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleReflect = async () => {
    setReflecting(true);
    try {
      const res = await api.reflect();
      setReflectResult(res.result);
      const idRes = await api.identity();
      setIdentity(idRes.identity);
    } catch (err) {
      setReflectResult(`Error: ${err}`);
    } finally {
      setReflecting(false);
    }
  };

  const handleExport = () => {
    if (!identity) return;
    const blob = new Blob(
      [JSON.stringify({ identity, exported: new Date().toISOString() }, null, 2)],
      { type: "application/json" }
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "cmk-identity.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div
          className="w-5 h-5 rounded-full border-2 animate-spin"
          style={{
            borderColor: "var(--border)",
            borderTopColor: "var(--accent)",
          }}
        />
      </div>
    );
  }

  const sections = identity ? parseIdentitySections(identity) : [];

  return (
    <div className="max-w-2xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-[20px] font-semibold tracking-tight">Identity</h2>
          <p className="text-[14px] mt-1" style={{ color: "var(--muted)" }}>
            How Claude sees you, based on accumulated memories.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExport}
            disabled={!identity}
            className="px-3 py-2 rounded-[var(--radius)] text-[13px] font-medium"
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border-light)",
              color: "var(--muted)",
              opacity: identity ? 1 : 0.5,
            }}
          >
            Export
          </button>
          <button
            onClick={handleReflect}
            disabled={reflecting}
            className="px-4 py-2 rounded-[var(--radius)] text-[14px] font-medium"
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              color: "var(--foreground)",
              boxShadow: "var(--shadow-xs)",
              opacity: reflecting ? 0.6 : 1,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "var(--surface-hover)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "var(--surface)";
            }}
          >
            {reflecting ? "Reflecting..." : "Reflect"}
          </button>
        </div>
      </div>

      {/* Stats grid */}
      {stats && (
        <div className="grid grid-cols-3 gap-3 mb-6">
          <MetricCard label="Memories" value={stats.total.toString()} />
          <MetricCard
            label="Active gates"
            value={Object.keys(stats.by_gate).length.toString()}
          />
          <MetricCard
            label="Identity"
            value={stats.has_identity ? "Active" : "None"}
            accent={stats.has_identity}
          />
        </div>
      )}

      {/* Identity sections */}
      {sections.length > 0 ? (
        sections.map((section, i) => (
          <IdentitySection
            key={i}
            title={section.title}
            content={section.content}
            gate={section.gate}
            onSave={(content) => {
              const updated = sections.map((s, j) =>
                j === i ? { ...s, content } : s
              );
              const newIdentity = updated
                .map((s) => `## ${s.title}\n${s.content}`)
                .join("\n\n");
              setIdentity(newIdentity);
              api.updateIdentity(newIdentity).catch(() => {});
            }}
          />
        ))
      ) : (
        <div
          className="rounded-[var(--radius)] p-6 mb-6"
          style={{
            background: "var(--warm-paper)",
            border: "1px solid var(--border-light)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <h3
            className="text-[12px] font-medium uppercase tracking-wider mb-4"
            style={{ color: "var(--sage)" }}
          >
            Identity Card
          </h3>
          <div
            className="text-[14px] leading-[1.4] whitespace-pre-wrap"
            style={{ fontFamily: "var(--font-serif)" }}
          >
            <span style={{ color: "var(--muted)" }}>
              No identity card yet. Click Reflect to generate one from your memories.
            </span>
          </div>
        </div>
      )}

      {/* Gate distribution */}
      {stats && Object.keys(stats.by_gate).length > 0 && (
        <div
          className="rounded-[var(--radius)] p-5 mt-3"
          style={{
            background: "var(--warm-paper)",
            border: "1px solid var(--border-light)",
            boxShadow: "var(--shadow-xs)",
          }}
        >
          <h3
            className="text-[12px] font-medium uppercase tracking-wider mb-4"
            style={{ color: "var(--sage)" }}
          >
            Distribution
          </h3>
          <div className="space-y-3">
            {Object.entries(stats.by_gate)
              .sort(([, a], [, b]) => b - a)
              .map(([gate, count]) => (
                <div key={gate} className="flex items-center gap-3">
                  <span
                    className="text-[12px] w-20 font-medium"
                    style={{ color: `var(--gate-${gate})` }}
                  >
                    {gate}
                  </span>
                  <div
                    className="flex-1 h-1.5 rounded-full overflow-hidden"
                    style={{ background: "var(--border-light)" }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${(count / (stats.total || 1)) * 100}%`,
                        background: `var(--gate-${gate})`,
                      }}
                    />
                  </div>
                  <span
                    className="text-[12px] w-8 text-right tabular-nums"
                    style={{ color: "var(--muted)" }}
                  >
                    {count}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Reflection result */}
      {reflectResult && (
        <div
          className="rounded-[var(--radius)] p-5 mt-6"
          style={{
            background: "var(--warm-paper)",
            border: "1px solid var(--border-light)",
            boxShadow: "var(--shadow-xs)",
          }}
        >
          <h3
            className="text-[12px] font-medium uppercase tracking-wider mb-3"
            style={{ color: "var(--sage)" }}
          >
            Reflection
          </h3>
          <pre
            className="text-[14px] leading-[1.4] whitespace-pre-wrap"
            style={{ fontFamily: "var(--font-serif)" }}
          >
            {reflectResult}
          </pre>
        </div>
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div
      className="rounded-[var(--radius)] p-4"
      style={{
        background: "var(--warm-paper)",
        border: "1px solid var(--border-light)",
        boxShadow: "var(--shadow-xs)",
      }}
    >
      <p
        className="text-[12px] uppercase tracking-wider font-medium"
        style={{ color: "var(--sage)" }}
      >
        {label}
      </p>
      <p
        className="text-[26px] font-semibold mt-1.5 tabular-nums tracking-tight"
        style={{ color: accent ? "var(--success)" : undefined }}
      >
        {value}
      </p>
    </div>
  );
}
