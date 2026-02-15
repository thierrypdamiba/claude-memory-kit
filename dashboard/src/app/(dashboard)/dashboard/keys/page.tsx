"use client";

import { useEffect, useState } from "react";
import { api, type ApiKey } from "@/lib/api";

export default function KeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [revealedKey, setRevealedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchKeys = async () => {
    try {
      const res = await api.listKeys();
      setKeys(res.keys);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load keys");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleCreate = async () => {
    setCreating(true);
    setError(null);
    try {
      const res = await api.createKey(newKeyName || "dashboard-key");
      setRevealedKey(res.key.key);
      setNewKeyName("");
      await fetchKeys();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create key");
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (id: string) => {
    try {
      await api.revokeKey(id);
      await fetchKeys();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to revoke key");
    }
  };

  const copyKey = () => {
    if (!revealedKey) return;
    navigator.clipboard.writeText(revealedKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div
          className="w-5 h-5 rounded-full border-2 animate-spin"
          style={{ borderColor: "var(--border)", borderTopColor: "var(--accent)" }}
        />
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-[20px] font-semibold tracking-tight mb-1">API Keys</h2>
      <p className="text-[14px] mb-6" style={{ color: "var(--muted)" }}>
        Manage API keys for programmatic access to your memory store.
      </p>

      {error && (
        <div
          className="rounded-[var(--radius)] px-4 py-3 mb-4 text-[14px]"
          style={{
            background: "rgba(220, 38, 38, 0.06)",
            border: "1px solid rgba(220, 38, 38, 0.15)",
            color: "var(--gate-correction)",
          }}
        >
          {error}
        </div>
      )}

      {/* One-time key reveal */}
      {revealedKey && (
        <div
          className="rounded-[var(--radius)] p-4 mb-6"
          style={{
            background: "rgba(5, 150, 105, 0.06)",
            border: "1px solid rgba(5, 150, 105, 0.15)",
          }}
        >
          <p className="text-[14px] font-medium mb-2">
            Key created. Copy it now, it won&apos;t be shown again.
          </p>
          <div className="flex items-center gap-2">
            <code
              className="flex-1 font-mono text-[13px] px-3 py-2 rounded-[var(--radius-sm)]"
              style={{ background: "var(--code-bg)", color: "var(--code-fg)" }}
            >
              {revealedKey}
            </code>
            <button
              onClick={copyKey}
              className="px-3 py-2 rounded-[var(--radius-sm)] text-[13px] font-medium shrink-0"
              style={{
                background: copied ? "var(--success)" : "var(--surface)",
                color: copied ? "#fff" : "var(--foreground)",
                border: copied ? "none" : "1px solid var(--border)",
              }}
            >
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
          <button
            onClick={() => setRevealedKey(null)}
            className="text-[13px] mt-2 underline underline-offset-2"
            style={{ color: "var(--muted)" }}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Create new key */}
      <div
        className="rounded-[var(--radius)] p-4 mb-6"
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border-light)",
          boxShadow: "var(--shadow-xs)",
        }}
      >
        <p className="text-[14px] font-medium mb-3">Create a new key</p>
        <div className="flex gap-2">
          <input
            type="text"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            placeholder="Key name (optional)"
            className="flex-1 px-3 py-2 rounded-[var(--radius-sm)] text-[14px] outline-none"
            style={{
              background: "var(--warm-paper)",
              border: "1px solid var(--border-light)",
              color: "var(--foreground)",
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = "var(--accent)";
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = "var(--border-light)";
            }}
          />
          <button
            onClick={handleCreate}
            disabled={creating}
            className="px-4 py-2 rounded-[var(--radius-sm)] text-[14px] font-medium shrink-0"
            style={{
              background: "var(--accent)",
              color: "#fff",
              opacity: creating ? 0.6 : 1,
            }}
          >
            {creating ? "Creating..." : "Create"}
          </button>
        </div>
      </div>

      {/* Keys table */}
      {keys.length === 0 ? (
        <div
          className="flex flex-col items-center justify-center h-32 gap-2"
          style={{ color: "var(--muted)" }}
        >
          <p className="text-[14px]">No API keys yet.</p>
        </div>
      ) : (
        <div
          className="rounded-[var(--radius)] overflow-hidden"
          style={{
            border: "1px solid var(--border-light)",
            boxShadow: "var(--shadow-xs)",
          }}
        >
          <table className="w-full text-[14px]">
            <thead>
              <tr
                style={{
                  background: "var(--warm-paper)",
                  borderBottom: "1px solid var(--border-light)",
                }}
              >
                <th className="text-left px-4 py-2.5 font-medium text-[12px] uppercase tracking-wider" style={{ color: "var(--sage)" }}>Prefix</th>
                <th className="text-left px-4 py-2.5 font-medium text-[12px] uppercase tracking-wider" style={{ color: "var(--sage)" }}>Name</th>
                <th className="text-left px-4 py-2.5 font-medium text-[12px] uppercase tracking-wider" style={{ color: "var(--sage)" }}>Created</th>
                <th className="text-left px-4 py-2.5 font-medium text-[12px] uppercase tracking-wider" style={{ color: "var(--sage)" }}>Last Used</th>
                <th className="text-left px-4 py-2.5 font-medium text-[12px] uppercase tracking-wider" style={{ color: "var(--sage)" }}>Status</th>
                <th className="text-right px-4 py-2.5 font-medium text-[12px] uppercase tracking-wider" style={{ color: "var(--sage)" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {keys.map((key) => (
                <tr
                  key={key.id}
                  style={{
                    borderBottom: "1px solid var(--border-light)",
                    background: "var(--surface)",
                  }}
                >
                  <td className="px-4 py-3 font-mono text-[13px]" style={{ color: "var(--dust)" }}>
                    {key.prefix}...
                  </td>
                  <td className="px-4 py-3">{key.name || "unnamed"}</td>
                  <td className="px-4 py-3 text-[13px]" style={{ color: "var(--muted)" }}>
                    {new Date(key.created).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-[13px]" style={{ color: "var(--muted)" }}>
                    {key.last_used
                      ? new Date(key.last_used).toLocaleDateString()
                      : "Never"}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className="inline-flex items-center gap-1.5 text-[12px] font-medium"
                      style={{
                        color: key.revoked ? "var(--gate-correction)" : "var(--success)",
                      }}
                    >
                      <span
                        className="w-1.5 h-1.5 rounded-full"
                        style={{
                          background: key.revoked ? "var(--gate-correction)" : "var(--success)",
                        }}
                      />
                      {key.revoked ? "Revoked" : "Active"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {!key.revoked && (
                      <button
                        onClick={() => handleRevoke(key.id)}
                        className="text-[13px] font-medium"
                        style={{ color: "var(--gate-correction)" }}
                      >
                        Revoke
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
