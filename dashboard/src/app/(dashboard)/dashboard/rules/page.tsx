"use client";

import { useEffect, useState } from "react";
import { api, type Rule } from "@/lib/api";

const SCOPES = ["global", "project", "person"];
const ENFORCEMENTS = ["suggest", "enforce", "warn"];

export default function RulesPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newCondition, setNewCondition] = useState("");
  const [newScope, setNewScope] = useState("global");
  const [newEnforcement, setNewEnforcement] = useState("suggest");

  const loadRules = () => {
    api
      .listRules()
      .then((res) => setRules(res.rules))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadRules();
  }, []);

  const handleCreate = async () => {
    if (!newCondition.trim()) return;
    setCreating(true);
    try {
      await api.createRule(newCondition.trim(), newScope, newEnforcement);
      setNewCondition("");
      setNewScope("global");
      setNewEnforcement("suggest");
      loadRules();
    } catch {
      // ignore
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteRule(id);
      setRules((prev) => prev.filter((r) => r.id !== id));
    } catch {
      // ignore
    }
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

  return (
    <div className="max-w-2xl">
      <h2 className="text-[20px] font-semibold tracking-tight mb-1">Rules</h2>
      <p className="text-[14px] mb-8" style={{ color: "var(--muted)" }}>
        Rules control how memories are stored, scored, and pruned. Define
        conditions and enforcement policies for your memory pipeline.
      </p>

      {/* Create rule form */}
      <div
        className="rounded-[var(--radius)] p-5 mb-6"
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border-light)",
          boxShadow: "var(--shadow-xs)",
        }}
      >
        <p
          className="text-[12px] font-medium uppercase tracking-wider mb-3"
          style={{ color: "var(--sage)" }}
        >
          New rule
        </p>

        <textarea
          value={newCondition}
          onChange={(e) => setNewCondition(e.target.value)}
          placeholder="e.g. If the user mentions a deadline, always store as promissory gate"
          className="w-full text-[14px] leading-[1.6] p-3 rounded-[var(--radius-sm)] outline-none resize-none min-h-[60px] mb-3"
          style={{
            background: "var(--warm-paper)",
            border: "1px solid var(--border)",
            color: "var(--foreground)",
          }}
        />

        <div className="flex items-center gap-3 mb-3">
          <div>
            <label
              className="text-[11px] font-medium uppercase tracking-wider block mb-1"
              style={{ color: "var(--muted)" }}
            >
              Scope
            </label>
            <select
              value={newScope}
              onChange={(e) => setNewScope(e.target.value)}
              className="text-[13px] px-2.5 py-1.5 rounded-[var(--radius-sm)] outline-none"
              style={{
                background: "var(--warm-paper)",
                border: "1px solid var(--border)",
                color: "var(--foreground)",
              }}
            >
              {SCOPES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label
              className="text-[11px] font-medium uppercase tracking-wider block mb-1"
              style={{ color: "var(--muted)" }}
            >
              Enforcement
            </label>
            <select
              value={newEnforcement}
              onChange={(e) => setNewEnforcement(e.target.value)}
              className="text-[13px] px-2.5 py-1.5 rounded-[var(--radius-sm)] outline-none"
              style={{
                background: "var(--warm-paper)",
                border: "1px solid var(--border)",
                color: "var(--foreground)",
              }}
            >
              {ENFORCEMENTS.map((e) => (
                <option key={e} value={e}>
                  {e}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={handleCreate}
          disabled={creating || !newCondition.trim()}
          className="px-4 py-2 rounded-[var(--radius)] text-[13px] font-medium"
          style={{
            background: "var(--foreground)",
            color: "var(--background)",
            opacity: creating || !newCondition.trim() ? 0.5 : 1,
          }}
        >
          {creating ? "Creating..." : "Create rule"}
        </button>
      </div>

      {/* Rules list */}
      {rules.length === 0 ? (
        <div
          className="rounded-[var(--radius)] p-6 text-center"
          style={{
            background: "var(--warm-paper)",
            border: "1px solid var(--border-light)",
          }}
        >
          <p className="text-[14px]" style={{ color: "var(--muted)" }}>
            No rules yet. Create your first rule above.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {rules.map((rule) => (
            <RuleCard key={rule.id} rule={rule} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
}

function RuleCard({
  rule,
  onDelete,
}: {
  rule: Rule;
  onDelete: (id: string) => void;
}) {
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    setDeleting(true);
    await onDelete(rule.id);
  };

  return (
    <div
      className="rounded-[var(--radius)] p-4"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border-light)",
        boxShadow: "var(--shadow-xs)",
      }}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span
            className="text-[12px] font-medium px-2 py-0.5 rounded-[4px] capitalize"
            style={{
              background: "var(--warm-paper)",
              color: "var(--muted)",
            }}
          >
            {rule.scope}
          </span>
          <span
            className="text-[12px] font-medium px-2 py-0.5 rounded-[4px] capitalize"
            style={{
              background:
                rule.enforcement === "enforce"
                  ? "rgba(220, 38, 38, 0.08)"
                  : rule.enforcement === "warn"
                    ? "rgba(217, 119, 6, 0.08)"
                    : "rgba(5, 150, 105, 0.08)",
              color:
                rule.enforcement === "enforce"
                  ? "var(--gate-correction)"
                  : rule.enforcement === "warn"
                    ? "var(--gate-behavioral)"
                    : "var(--gate-promissory)",
            }}
          >
            {rule.enforcement}
          </span>
        </div>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="text-[12px] font-medium"
          style={{
            color: "var(--gate-correction)",
            opacity: deleting ? 0.5 : 1,
          }}
        >
          {deleting ? "..." : "Delete"}
        </button>
      </div>
      <p className="text-[14px] leading-[1.5]">{rule.condition}</p>
      {rule.last_triggered && (
        <p className="text-[12px] mt-2" style={{ color: "var(--dust)" }}>
          Last triggered: {new Date(rule.last_triggered).toLocaleString()}
        </p>
      )}
      <p className="text-[11px] mt-1" style={{ color: "var(--dust)" }}>
        Created {new Date(rule.created).toLocaleDateString()}
      </p>
    </div>
  );
}
