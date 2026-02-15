"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const SIDEBAR_LINKS = [
  { href: "/docs", label: "Quickstart" },
  { href: "/docs/install", label: "Install" },
  { href: "/docs/mcp", label: "MCP Config" },
  { href: "/docs/api", label: "API Reference" },
  { href: "/docs/cli", label: "CLI Reference" },
];

export function DocsSidebar() {
  const pathname = usePathname();

  return (
    <nav
      className="w-56 shrink-0 py-8 pr-6"
      style={{ borderRight: "1px solid var(--border-light)" }}
    >
      <p
        className="text-[11px] font-medium uppercase tracking-wider mb-4 px-3"
        style={{ color: "var(--muted-light)" }}
      >
        Documentation
      </p>
      <div className="space-y-0.5">
        {SIDEBAR_LINKS.map((link) => {
          const active = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className="block px-3 py-2 rounded-[var(--radius-sm)] text-[14px]"
              style={{
                color: active ? "var(--foreground)" : "var(--muted)",
                fontWeight: active ? 500 : 400,
                background: active ? "var(--surface-active)" : "transparent",
                transition: "color 140ms ease, background 140ms ease",
              }}
              onMouseEnter={(e) => {
                if (!active) {
                  e.currentTarget.style.background = "var(--surface-hover)";
                  e.currentTarget.style.color = "var(--foreground)";
                }
              }}
              onMouseLeave={(e) => {
                if (!active) {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.color = "var(--muted)";
                }
              }}
            >
              {link.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
