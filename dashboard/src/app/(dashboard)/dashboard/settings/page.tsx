"use client";

import { useEffect, useState } from "react";
import { api, type Stats } from "@/lib/api";
import { useLocalStorage } from "@/hooks/use-local-storage";

export default function SettingsPage() {
  const [user, setUser] = useState<Record<string, string> | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [mode, setMode] = useState<string>("local");
  const [vectorStore, setVectorStore] = useState<string>("local");
  const [loading, setLoading] = useState(true);
  const [theme, setTheme] = useLocalStorage<"system" | "light" | "dark">(
    "cmk-theme",
    "system"
  );
  const [compactCards, setCompactCards] = useLocalStorage(
    "cmk-compact-cards",
    false
  );

  useEffect(() => {
    Promise.all([
      api.me().catch(() => ({ user: null })),
      api.stats().catch(() => null),
      api.mode().catch(() => ({ mode: "local", vector_store: "local" })),
    ])
      .then(([meRes, statsRes, modeRes]) => {
        if (meRes.user) setUser(meRes.user as Record<string, string>);
        if (statsRes) setStats(statsRes);
        setMode(modeRes.mode);
        setVectorStore(modeRes.vector_store);
      })
      .finally(() => setLoading(false));
  }, []);

  const isCloud = mode === "cloud";

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
    <div className="max-w-xl">
      <h2 className="text-[20px] font-semibold tracking-tight mb-1">Settings</h2>
      <p className="text-[14px] mb-8" style={{ color: "var(--muted)" }}>
        Account, data, and preferences.
      </p>

      {/* Mode indicator */}
      <Section title="Mode">
        <div className="flex items-center gap-3">
          <span
            className="w-2 h-2 rounded-full"
            style={{
              background: isCloud ? "var(--gate-relational)" : "var(--success)",
            }}
          />
          <span className="text-[14px] font-medium">
            {isCloud ? "Cloud Sync" : "Local"}
          </span>
        </div>
        <p className="text-[13px] mt-1.5" style={{ color: "var(--muted)" }}>
          {isCloud
            ? "Your memories sync to the cloud and are accessible across devices."
            : "Memories are stored locally on your machine only."}
        </p>
        <p className="text-[12px] mt-1 font-mono" style={{ color: "var(--dust)" }}>
          vector store: {vectorStore}
        </p>
      </Section>

      {/* Account info */}
      {user && user.id !== "local" && (
        <Section title="Account">
          <InfoRow label="Email" value={user.email || "Not set"} />
          <InfoRow label="User ID" value={user.id} mono />
          <InfoRow label="Plan" value={user.plan || "free"} />
        </Section>
      )}

      {/* Data */}
      <Section title="Data">
        <InfoRow
          label="Total memories"
          value={stats?.total?.toString() || "0"}
        />
        <InfoRow
          label="Active gates"
          value={
            stats ? Object.keys(stats.by_gate).length.toString() : "0"
          }
        />
        <InfoRow
          label="Identity"
          value={stats?.has_identity ? "Active" : "None"}
        />
        <div className="flex gap-2 mt-4">
          <button
            className="px-3.5 py-2 rounded-[var(--radius-sm)] text-[13px] font-medium"
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              color: "var(--foreground)",
            }}
            onClick={() => {
              window.open(
                `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:7749"}/api/memories?limit=9999`,
                "_blank"
              );
            }}
          >
            Export memories (JSON)
          </button>
          <button
            className="px-3.5 py-2 rounded-[var(--radius-sm)] text-[13px] font-medium"
            style={{
              background: "transparent",
              border: "1px solid rgba(220, 38, 38, 0.2)",
              color: "var(--gate-correction)",
            }}
            onClick={() => {
              if (confirm("Clear all local dashboard preferences?")) {
                localStorage.clear();
                window.location.reload();
              }
            }}
          >
            Clear local data
          </button>
        </div>
      </Section>

      {/* Preferences */}
      <Section title="Preferences">
        <div className="space-y-4">
          <div>
            <label className="text-[13px] font-medium block mb-1.5">
              Theme
            </label>
            <div className="flex gap-2">
              {(["system", "light", "dark"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTheme(t)}
                  className="px-3 py-1.5 rounded-[var(--radius-sm)] text-[13px] capitalize"
                  style={{
                    background:
                      theme === t ? "var(--surface-active)" : "var(--surface)",
                    border: `1px solid ${theme === t ? "var(--accent)" : "var(--border-light)"}`,
                    color:
                      theme === t ? "var(--foreground)" : "var(--muted)",
                    fontWeight: theme === t ? 500 : 400,
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[14px] font-medium">Compact cards</p>
              <p className="text-[13px]" style={{ color: "var(--muted)" }}>
                Show less metadata on memory cards.
              </p>
            </div>
            <button
              onClick={() => setCompactCards(!compactCards)}
              className="w-10 h-5 rounded-full relative"
              style={{
                background: compactCards
                  ? "var(--accent)"
                  : "var(--border)",
                transition: "background 140ms ease",
              }}
            >
              <span
                className="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm"
                style={{
                  left: compactCards ? 22 : 2,
                  transition: "left 140ms ease",
                }}
              />
            </button>
          </div>
        </div>
      </Section>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className="rounded-[var(--radius)] p-5 mb-4"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border-light)",
        boxShadow: "var(--shadow-xs)",
      }}
    >
      <h3
        className="text-[12px] font-medium uppercase tracking-wider mb-4"
        style={{ color: "var(--sage)" }}
      >
        {title}
      </h3>
      {children}
    </div>
  );
}

function InfoRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-[14px]" style={{ color: "var(--muted)" }}>
        {label}
      </span>
      <span
        className={`text-[14px] ${mono ? "font-mono text-[13px]" : ""}`}
        style={{ color: "var(--foreground)" }}
      >
        {value}
      </span>
    </div>
  );
}
