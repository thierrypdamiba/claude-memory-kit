"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton } from "./user-button";

const MEMORY_NAV = [
  { href: "/dashboard", label: "Timeline", icon: "\u25F7" },
  { href: "/dashboard/search", label: "Search", icon: "\u2315" },
  { href: "/dashboard/graph", label: "Graph", icon: "\u25C9" },
  { href: "/dashboard/identity", label: "Identity", icon: "\u25C7" },
];

const MANAGE_NAV = [
  { href: "/dashboard/private", label: "Private", icon: "\u26A0" },
  { href: "/dashboard/rules", label: "Rules", icon: "\u2630" },
  { href: "/dashboard/keys", label: "Keys", icon: "\u26BF" },
  { href: "/dashboard/settings", label: "Settings", icon: "\u2699" },
  { href: "/dashboard/setup", label: "Setup", icon: "\u25CB" },
];

export function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  };

  return (
    <aside
      className="w-56 h-screen fixed left-0 top-0 flex flex-col"
      style={{
        borderRight: "1px solid var(--border-light)",
        background: "var(--surface)",
      }}
    >
      {/* Header */}
      <div className="px-5 pt-5 pb-4 flex items-center justify-between">
        <div>
          <h1
            className="text-[14px] font-semibold tracking-tight"
            style={{ color: "var(--foreground)" }}
          >
            CMK
          </h1>
          <p className="text-[12px] mt-0.5" style={{ color: "var(--muted-light)" }}>
            claude memory kit
          </p>
        </div>
        <UserButton />
      </div>

      {/* Divider */}
      <div
        className="mx-4 mb-2"
        style={{ borderTop: "1px solid var(--border-light)" }}
      />

      {/* Navigation */}
      <nav className="flex-1 px-3 overflow-y-auto">
        <SectionLabel>Memory</SectionLabel>
        {MEMORY_NAV.map((item) => (
          <NavItem
            key={item.href}
            href={item.href}
            label={item.label}
            icon={item.icon}
            active={isActive(item.href)}
          />
        ))}

        <SectionLabel className="mt-5">Manage</SectionLabel>
        {MANAGE_NAV.map((item) => (
          <NavItem
            key={item.href}
            href={item.href}
            label={item.label}
            icon={item.icon}
            active={isActive(item.href)}
          />
        ))}
      </nav>

      {/* Footer */}
      <div
        className="px-5 py-3 text-[12px]"
        style={{
          color: "var(--dust)",
          borderTop: "1px solid var(--border-light)",
        }}
      >
        v0.1.0
      </div>
    </aside>
  );
}

function SectionLabel({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <p
      className={`text-[11px] font-medium uppercase tracking-wider px-3 mb-1.5 ${className}`}
      style={{ color: "var(--dust)" }}
    >
      {children}
    </p>
  );
}

function NavItem({
  href,
  label,
  icon,
  active,
}: {
  href: string;
  label: string;
  icon: string;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      className="flex items-center gap-3 px-3 py-[7px] rounded-[var(--radius-sm)] text-[14px] mb-px"
      style={{
        background: active ? "var(--surface-active)" : "transparent",
        color: active ? "var(--foreground)" : "var(--sage)",
        fontWeight: active ? 500 : 400,
        transition: "background 140ms ease, color 140ms ease",
      }}
      onMouseEnter={(e) => {
        if (!active)
          e.currentTarget.style.background = "var(--surface-hover)";
      }}
      onMouseLeave={(e) => {
        if (!active) e.currentTarget.style.background = "transparent";
      }}
    >
      <span className="text-[16px] w-5 text-center opacity-60">
        {icon}
      </span>
      {label}
    </Link>
  );
}
