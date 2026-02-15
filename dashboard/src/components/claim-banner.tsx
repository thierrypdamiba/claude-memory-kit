"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function ClaimBanner() {
  const [count, setCount] = useState(0);
  const [visible, setVisible] = useState(false);
  const [claiming, setClaiming] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    api
      .checkLocalData()
      .then((res) => {
        if (res.has_local_data) {
          setCount(res.counts.total || 0);
          setVisible(true);
        }
      })
      .catch(() => {});
  }, []);

  const handleClaim = async () => {
    setClaiming(true);
    try {
      await api.claimLocal();
      setDone(true);
      setTimeout(() => setVisible(false), 3000);
    } catch {
      setClaiming(false);
    }
  };

  if (!visible) return null;

  return (
    <div
      className="rounded-[var(--radius)] px-4 py-3 mb-6 flex items-center justify-between"
      style={{
        background: done ? "rgba(5, 150, 105, 0.06)" : "rgba(192, 86, 33, 0.06)",
        border: `1px solid ${done ? "rgba(5, 150, 105, 0.2)" : "rgba(192, 86, 33, 0.15)"}`,
        animation: "drift-up 200ms ease",
      }}
    >
      {done ? (
        <div className="flex items-center gap-2">
          <span style={{ color: "var(--gate-promissory)" }}>&#10003;</span>
          <p className="text-[14px] font-medium" style={{ color: "var(--gate-promissory)" }}>
            Claimed. Your local memories are now linked to your account.
          </p>
        </div>
      ) : (
        <>
          <div>
            <p className="text-[14px] font-medium">
              {count} unclaimed local {count === 1 ? "memory" : "memories"}
            </p>
            <p className="text-[13px] mt-0.5" style={{ color: "var(--muted)" }}>
              Link them to your account to access everywhere.
            </p>
          </div>
          <button
            onClick={handleClaim}
            disabled={claiming}
            className="px-3.5 py-1.5 rounded-[var(--radius-sm)] text-[14px] font-medium shrink-0"
            style={{
              background: "var(--accent)",
              color: "#fff",
              opacity: claiming ? 0.6 : 1,
              transition: "transform 140ms ease, opacity 140ms ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-1px)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "translateY(0)";
            }}
          >
            {claiming ? "Claiming..." : "Claim"}
          </button>
        </>
      )}
    </div>
  );
}
