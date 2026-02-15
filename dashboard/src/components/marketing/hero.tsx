"use client";

import { useState } from "react";
import Link from "next/link";

const WITHOUT_MESSAGES = [
  { role: "user" as const, text: "Open the config file for me." },
  { role: "assistant" as const, text: "Sure! What editor do you use?" },
  { role: "user" as const, text: "...I told you last session. VS Code." },
];

const WITH_MESSAGES = [
  { role: "user" as const, text: "Open the config file for me." },
  {
    role: "assistant" as const,
    text: "Opening in VS Code since that's your preferred editor.",
    memory: true,
  },
];

const TRUST_PILLS = ["Works instantly", "Editable", "Scoped"];

export function Hero() {
  const [activeTab, setActiveTab] = useState<"without" | "with">("without");

  return (
    <section
      className="max-w-4xl mx-auto px-6 pt-24 pb-20"
      style={{ animation: "drift-up 400ms ease both" }}
    >
      {/* Headline */}
      <h1
        className="text-[52px] md:text-[64px] font-normal tracking-tight leading-[1.05] mb-6"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        Claude remembers now.
      </h1>

      {/* Subhead */}
      <p
        className="text-[18px] leading-[1.65] mb-10 max-w-xl"
        style={{ color: "var(--muted)" }}
      >
        Persistent memory for Claude, powered by MCP. Sign up, add your API
        key, and Claude remembers everything across sessions.
      </p>

      {/* CTAs */}
      <div className="flex items-center gap-4 mb-16">
        <Link
          href="/sign-up"
          className="px-6 py-3 rounded-[var(--radius)] text-[15px] font-medium"
          style={{
            background: "var(--foreground)",
            color: "var(--background)",
            transition: "opacity 140ms ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.opacity = "0.85";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.opacity = "1";
          }}
        >
          Get started
        </Link>
        <a
          href="#recall-proof"
          className="px-6 py-3 rounded-[var(--radius)] text-[15px] font-medium"
          style={{
            background: "transparent",
            border: "1px solid var(--border)",
            color: "var(--foreground)",
            transition: "background 140ms ease, border-color 140ms ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "var(--surface-hover)";
            e.currentTarget.style.borderColor = "var(--muted-light)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "transparent";
            e.currentTarget.style.borderColor = "var(--border)";
          }}
        >
          Watch recall
        </a>
      </div>

      {/* Continuity demo card */}
      <div
        className="rounded-[var(--radius-lg)] overflow-hidden"
        style={{
          border: "1px solid var(--border)",
          boxShadow: "var(--shadow-md)",
          background: "var(--surface)",
        }}
      >
        {/* Tabs */}
        <div
          className="flex"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <button
            onClick={() => setActiveTab("without")}
            className="flex-1 px-5 py-3 text-[14px] font-medium"
            style={{
              color:
                activeTab === "without"
                  ? "var(--foreground)"
                  : "var(--muted-light)",
              background:
                activeTab === "without"
                  ? "var(--surface)"
                  : "var(--warm-paper)",
              borderBottom:
                activeTab === "without"
                  ? "2px solid var(--foreground)"
                  : "2px solid transparent",
              transition: "all 200ms ease",
            }}
          >
            Without CMK
          </button>
          <button
            onClick={() => setActiveTab("with")}
            className="flex-1 px-5 py-3 text-[14px] font-medium"
            style={{
              color:
                activeTab === "with"
                  ? "var(--foreground)"
                  : "var(--muted-light)",
              background:
                activeTab === "with" ? "var(--surface)" : "var(--warm-paper)",
              borderBottom:
                activeTab === "with"
                  ? "2px solid var(--gate-promissory)"
                  : "2px solid transparent",
              transition: "all 200ms ease",
            }}
          >
            With CMK
          </button>
        </div>

        {/* Chat messages */}
        <div className="p-6 min-h-[180px]">
          {activeTab === "without" ? (
            <div className="space-y-4">
              {WITHOUT_MESSAGES.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  style={{
                    animation: `drift-up 200ms ease ${i * 80}ms both`,
                  }}
                >
                  <div
                    className="max-w-[80%] px-4 py-2.5 rounded-[var(--radius)]"
                    style={{
                      background:
                        msg.role === "user"
                          ? "var(--foreground)"
                          : "var(--warm-paper)",
                      color:
                        msg.role === "user"
                          ? "var(--background)"
                          : "var(--foreground)",
                      fontSize: "14px",
                      lineHeight: "1.5",
                    }}
                  >
                    {msg.text}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-4">
              {WITH_MESSAGES.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  style={{
                    animation: `drift-up 200ms ease ${i * 80}ms both`,
                  }}
                >
                  <div className="max-w-[80%]">
                    <div
                      className="px-4 py-2.5 rounded-[var(--radius)]"
                      style={{
                        background:
                          msg.role === "user"
                            ? "var(--foreground)"
                            : "var(--warm-paper)",
                        color:
                          msg.role === "user"
                            ? "var(--background)"
                            : "var(--foreground)",
                        fontSize: "14px",
                        lineHeight: "1.5",
                      }}
                    >
                      {msg.text}
                    </div>
                    {"memory" in msg && msg.memory && (
                      <div
                        className="inline-flex items-center gap-1.5 mt-2 px-2.5 py-1 rounded-full text-[11px] font-medium"
                        style={{
                          background: "rgba(5, 150, 105, 0.1)",
                          color: "var(--gate-promissory)",
                          animation: "drift-up 300ms ease 200ms both",
                        }}
                      >
                        <svg
                          width="12"
                          height="12"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M12 2a4 4 0 0 1 4 4v2H8V6a4 4 0 0 1 4-4z" />
                          <rect x="3" y="8" width="18" height="14" rx="2" />
                          <circle cx="12" cy="16" r="2" />
                        </svg>
                        recalled from memory
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Trust strip */}
      <div className="flex items-center justify-center gap-3 mt-10">
        {TRUST_PILLS.map((pill) => (
          <span
            key={pill}
            className="px-3.5 py-1.5 rounded-full text-[12px] font-medium"
            style={{
              background: "var(--warm-paper)",
              color: "var(--muted)",
              border: "1px solid var(--border-light)",
            }}
          >
            {pill}
          </span>
        ))}
      </div>
    </section>
  );
}
