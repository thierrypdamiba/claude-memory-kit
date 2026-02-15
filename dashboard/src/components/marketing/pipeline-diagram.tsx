"use client";

import { useEffect, useState } from "react";

const STEPS = [
  {
    label: "Claude",
    description: "Generates a message or response",
  },
  {
    label: "MCP",
    description: "Intercepts via tool calls",
  },
  {
    label: "Gates",
    description: "Classifies the memory type",
  },
  {
    label: "Storage",
    description: "Embeds and persists locally",
  },
  {
    label: "Recall",
    description: "Retrieved on next session",
  },
];

export function PipelineDiagram() {
  const [visibleCount, setVisibleCount] = useState(0);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          let count = 0;
          const interval = setInterval(() => {
            count += 1;
            setVisibleCount(count);
            if (count >= STEPS.length * 2 - 1) {
              clearInterval(interval);
            }
          }, 180);
          observer.disconnect();
        }
      },
      { threshold: 0.3 }
    );

    const el = document.getElementById("pipeline-section");
    if (el) observer.observe(el);

    return () => observer.disconnect();
  }, []);

  return (
    <section id="pipeline-section" className="max-w-4xl mx-auto px-6 py-20">
      <h2
        className="text-[32px] font-normal tracking-tight mb-2"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        How it works
      </h2>
      <p
        className="text-[15px] leading-[1.6] mb-12"
        style={{ color: "var(--muted)" }}
      >
        From conversation to persistent recall in five steps.
      </p>

      {/* Desktop: horizontal flow */}
      <div className="hidden md:flex items-start justify-between gap-0">
        {STEPS.map((step, i) => {
          const pillIndex = i * 2;
          const lineIndex = i * 2 + 1;
          const pillVisible = pillIndex < visibleCount;
          const lineVisible = lineIndex < visibleCount;

          return (
            <div
              key={i}
              className="flex items-start"
              style={{ flex: i < STEPS.length - 1 ? 1 : "0 0 auto" }}
            >
              {/* Pill node */}
              <div
                className="flex flex-col items-center"
                style={{
                  opacity: pillVisible ? 1 : 0,
                  transform: pillVisible
                    ? "translateY(0)"
                    : "translateY(8px)",
                  transition: "opacity 300ms ease, transform 300ms ease",
                  minWidth: 100,
                }}
              >
                <div
                  className="px-4 py-2 rounded-full text-[14px] font-medium whitespace-nowrap"
                  style={{
                    background: "var(--foreground)",
                    color: "var(--background)",
                  }}
                >
                  {step.label}
                </div>
                <p
                  className="text-[12px] mt-2 text-center leading-[1.4] max-w-[110px]"
                  style={{ color: "var(--muted)" }}
                >
                  {step.description}
                </p>
              </div>

              {/* Connecting line */}
              {i < STEPS.length - 1 && (
                <div
                  className="flex items-center self-center mt-[-12px]"
                  style={{ flex: 1, minWidth: 24, padding: "0 4px" }}
                >
                  <div
                    style={{
                      height: 2,
                      background: "var(--border)",
                      flex: 1,
                      transformOrigin: "left",
                      transform: lineVisible ? "scaleX(1)" : "scaleX(0)",
                      transition: "transform 300ms ease",
                    }}
                  />
                  <svg
                    width="8"
                    height="10"
                    viewBox="0 0 8 10"
                    fill="none"
                    style={{
                      opacity: lineVisible ? 1 : 0,
                      transition: "opacity 200ms ease 100ms",
                    }}
                  >
                    <path
                      d="M1 1L6 5L1 9"
                      stroke="var(--border)"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Mobile: vertical flow */}
      <div className="md:hidden space-y-3">
        {STEPS.map((step, i) => {
          const pillIndex = i * 2;
          const pillVisible = pillIndex < visibleCount;

          return (
            <div key={i}>
              <div
                className="flex items-center gap-4 px-4 py-3 rounded-[var(--radius)]"
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  opacity: pillVisible ? 1 : 0,
                  transform: pillVisible
                    ? "translateY(0)"
                    : "translateY(8px)",
                  transition: "opacity 300ms ease, transform 300ms ease",
                }}
              >
                <span
                  className="text-[12px] font-mono font-medium w-5 text-center"
                  style={{ color: "var(--muted-light)" }}
                >
                  {i + 1}
                </span>
                <div>
                  <p className="text-[14px] font-medium">{step.label}</p>
                  <p
                    className="text-[12px] leading-[1.4]"
                    style={{ color: "var(--muted)" }}
                  >
                    {step.description}
                  </p>
                </div>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className="flex justify-center py-1"
                  style={{ color: "var(--border)" }}
                >
                  <svg
                    width="10"
                    height="12"
                    viewBox="0 0 10 12"
                    fill="none"
                  >
                    <path
                      d="M5 1L5 9M5 9L1 5.5M5 9L9 5.5"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
