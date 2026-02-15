"use client";

import { useState, useRef, useEffect } from "react";
import { useScope, type Scope } from "@/hooks/use-scope";

const SCOPES: { value: Scope; label: string }[] = [
  { value: "workspace", label: "Workspace" },
  { value: "project", label: "Project" },
  { value: "person", label: "Person" },
];

export function ScopePill() {
  const { scope, setScope } = useScope();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const current = SCOPES.find((s) => s.value === scope) || SCOPES[0];

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[12px] font-medium"
        style={{
          background: "var(--warm-paper)",
          border: "1px solid var(--border-light)",
          color: "var(--muted)",
          transition: "border-color 140ms ease",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = "var(--border)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = "var(--border-light)";
        }}
      >
        {current.label}
        <svg
          width="10"
          height="10"
          viewBox="0 0 10 10"
          fill="currentColor"
          style={{
            transform: open ? "rotate(180deg)" : "rotate(0)",
            transition: "transform 140ms ease",
          }}
        >
          <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" fill="none" strokeWidth="1.2" />
        </svg>
      </button>

      {open && (
        <div
          className="absolute top-full left-0 mt-1 py-1 rounded-[var(--radius-sm)] min-w-[120px] z-50"
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border-light)",
            boxShadow: "var(--shadow-md)",
          }}
        >
          {SCOPES.map((s) => (
            <button
              key={s.value}
              onClick={() => {
                setScope(s.value);
                setOpen(false);
              }}
              className="block w-full text-left px-3 py-1.5 text-[13px]"
              style={{
                background:
                  scope === s.value ? "var(--surface-active)" : "transparent",
                color:
                  scope === s.value ? "var(--foreground)" : "var(--muted)",
                fontWeight: scope === s.value ? 500 : 400,
              }}
              onMouseEnter={(e) => {
                if (scope !== s.value)
                  e.currentTarget.style.background = "var(--surface-hover)";
              }}
              onMouseLeave={(e) => {
                if (scope !== s.value)
                  e.currentTarget.style.background = "transparent";
              }}
            >
              {s.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
