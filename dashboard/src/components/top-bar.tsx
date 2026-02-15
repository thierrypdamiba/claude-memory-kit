"use client";

import { Suspense, useState } from "react";
import { useRouter } from "next/navigation";
import { ModeBadge } from "./mode-badge";
import { ScopePill } from "./scope-pill";

export function TopBar() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    router.push(`/dashboard/search?q=${encodeURIComponent(query.trim())}`);
    setQuery("");
  };

  return (
    <header
      className="h-12 flex items-center justify-between px-6 shrink-0"
      style={{
        borderBottom: "1px solid var(--border-light)",
        background: "var(--surface)",
      }}
    >
      {/* Left: scope pill */}
      <div className="flex items-center gap-3">
        <Suspense fallback={null}>
          <ScopePill />
        </Suspense>
      </div>

      {/* Center: search */}
      <form onSubmit={handleSearch} className="flex-1 max-w-md mx-8">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search memories..."
          className="w-full px-3 py-1.5 rounded-[var(--radius-sm)] text-[13px] outline-none"
          style={{
            background: "var(--warm-paper)",
            border: "1px solid transparent",
            color: "var(--foreground)",
          }}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = "var(--border)";
            e.currentTarget.style.background = "var(--surface)";
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = "transparent";
            e.currentTarget.style.background = "var(--warm-paper)";
          }}
        />
      </form>

      {/* Right: mode badge */}
      <div className="flex items-center gap-3">
        <ModeBadge />
      </div>
    </header>
  );
}
