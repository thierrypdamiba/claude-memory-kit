"use client";

import Link from "next/link";

const FOOTER_LINKS = [
  { label: "Security", href: "/docs/security" },
  { label: "Local-first architecture", href: "/docs/architecture" },
  { label: "GitHub", href: "https://github.com/thierrydamiba/claude-memory" },
  { label: "Open-source", href: "/docs/license" },
];

export function CTA() {
  return (
    <section className="max-w-4xl mx-auto px-6 pt-20 pb-24">
      {/* CTA block */}
      <div className="text-center mb-10">
        <h2
          className="text-[36px] md:text-[44px] font-normal tracking-tight mb-6"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          Give Claude a memory.
        </h2>
        <div className="flex items-center justify-center gap-4">
          <Link
            href="/sign-up"
            className="px-6 py-3 rounded-[var(--radius)] text-[15px] font-medium"
            style={{
              background: "var(--foreground)",
              color: "var(--background)",
              transition: "opacity 140ms ease",
            }}
            onMouseEnter={(e: React.MouseEvent<HTMLAnchorElement>) => {
              e.currentTarget.style.opacity = "0.85";
            }}
            onMouseLeave={(e: React.MouseEvent<HTMLAnchorElement>) => {
              e.currentTarget.style.opacity = "1";
            }}
          >
            Get started
          </Link>
          <Link
            href="/docs"
            className="px-6 py-3 rounded-[var(--radius)] text-[15px] font-medium"
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--foreground)",
              transition: "background 140ms ease, border-color 140ms ease",
            }}
            onMouseEnter={(e: React.MouseEvent<HTMLAnchorElement>) => {
              e.currentTarget.style.background = "var(--surface-hover)";
              e.currentTarget.style.borderColor = "var(--muted-light)";
            }}
            onMouseLeave={(e: React.MouseEvent<HTMLAnchorElement>) => {
              e.currentTarget.style.background = "transparent";
              e.currentTarget.style.borderColor = "var(--border)";
            }}
          >
            Read the docs
          </Link>
        </div>
      </div>

      {/* Divider */}
      <div
        className="my-12"
        style={{ borderTop: "1px solid var(--border-light)" }}
      />

      {/* Footer links */}
      <div className="flex items-center justify-center gap-6 flex-wrap">
        {FOOTER_LINKS.map((link) => (
          <Link
            key={link.label}
            href={link.href}
            className="text-[13px]"
            style={{
              color: "var(--muted)",
              transition: "color 140ms ease",
            }}
            onMouseEnter={(e: React.MouseEvent<HTMLAnchorElement>) => {
              e.currentTarget.style.color = "var(--foreground)";
            }}
            onMouseLeave={(e: React.MouseEvent<HTMLAnchorElement>) => {
              e.currentTarget.style.color = "var(--muted)";
            }}
            {...(link.href.startsWith("http")
              ? { target: "_blank", rel: "noopener noreferrer" }
              : {})}
          >
            {link.label}
          </Link>
        ))}
      </div>
    </section>
  );
}
