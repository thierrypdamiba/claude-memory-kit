"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";

const FEATURES = [
  { label: "5 memory gates", detail: "behavioral, relational, epistemic, promissory, correction" },
  { label: "Local or cloud", detail: "SQLite locally, or sync across devices with an account" },
  { label: "MCP native", detail: "works with any MCP-compatible client" },
];

// Each scene is a sequence of lines that type out
const SCENES = [
  {
    label: "session 1",
    lines: [
      { speaker: "you", text: "We're building a Rust API for the chess engine. Target is sub-10ms per move." },
      { speaker: "claude", text: 'Got it. I\'ll keep latency as the primary constraint.' },
      { speaker: "system", text: "saved [epistemic] Rust API for chess engine, sub-10ms target" },
      { speaker: "you", text: "Alex from the ML team said we can't use async for the eval loop. It breaks their CUDA bindings." },
      { speaker: "claude", text: "Important constraint. Sync eval loop it is." },
      { speaker: "system", text: "saved [relational] Alex (ML team): no async in eval loop, breaks CUDA bindings" },
    ],
  },
  {
    label: "session 2 (next day)",
    lines: [
      { speaker: "you", text: "Let's add concurrency to the eval loop." },
      { speaker: "claude", text: "Heads up: Alex from the ML team said async breaks their CUDA bindings. Want to check with him first, or use a thread pool instead?" },
      { speaker: "system", text: "recalled [relational] Alex (ML team): no async in eval loop" },
      { speaker: "you", text: "Oh right. Thread pool works. Also, I talked to Alex and he actually left the ML team. Sarah is the new lead." },
      { speaker: "claude", text: "Updated. Sarah is the ML team lead now." },
      { speaker: "system", text: "saved [correction] Sarah replaced Alex as ML team lead" },
    ],
  },
  {
    label: "session 3 (a week later)",
    lines: [
      { speaker: "you", text: "Set up the deployment pipeline." },
      { speaker: "claude", text: "Building the pipeline for the Rust chess API. Using sync thread pool for the eval loop per Sarah's team constraints. Targeting sub-10ms latency. Want me to add benchmark gates to the CI?" },
      { speaker: "you", text: "...you remembered all of that?" },
      { speaker: "claude", text: "That's what I'm here for." },
    ],
  },
];

const TYPING_SPEED = 18;   // ms per character
const LINE_PAUSE = 600;    // ms between lines
const SCENE_PAUSE = 2000;  // ms between scenes
const END_PAUSE = 4000;    // ms before restarting

export function Hero() {
  const [copied, setCopied] = useState(false);
  const [visibleLines, setVisibleLines] = useState<
    { sceneIdx: number; lineIdx: number; chars: number }[]
  >([]);
  const [currentScene, setCurrentScene] = useState(0);
  const animRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const installCmd = "uv tool install claude-memory-kit";

  function handleCopy() {
    navigator.clipboard.writeText(installCmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  useEffect(() => {
    let cancelled = false;

    async function sleep(ms: number) {
      return new Promise<void>((resolve) => {
        animRef.current = setTimeout(() => {
          if (!cancelled) resolve();
        }, ms);
      });
    }

    async function animate() {
      while (!cancelled) {
        for (let si = 0; si < SCENES.length && !cancelled; si++) {
          setCurrentScene(si);
          const scene = SCENES[si];

          for (let li = 0; li < scene.lines.length && !cancelled; li++) {
            const line = scene.lines[li];
            const totalChars = line.text.length;

            // Type out character by character
            for (let c = 0; c <= totalChars && !cancelled; c++) {
              setVisibleLines((prev) => {
                const existing = prev.filter(
                  (l) => !(l.sceneIdx === si && l.lineIdx === li)
                );
                return [...existing, { sceneIdx: si, lineIdx: li, chars: c }];
              });
              if (c < totalChars) await sleep(TYPING_SPEED);
            }

            // Scroll to bottom
            if (containerRef.current) {
              containerRef.current.scrollTop = containerRef.current.scrollHeight;
            }

            await sleep(LINE_PAUSE);
          }

          if (si < SCENES.length - 1) {
            await sleep(SCENE_PAUSE);
          }
        }

        await sleep(END_PAUSE);

        // Reset for loop
        setVisibleLines([]);
        setCurrentScene(0);
      }
    }

    animate();

    return () => {
      cancelled = true;
      if (animRef.current) clearTimeout(animRef.current);
    };
  }, []);

  function renderLine(
    sceneIdx: number,
    lineIdx: number,
    line: { speaker: string; text: string },
    chars: number
  ) {
    const text = line.text.slice(0, chars);
    const cursor = chars < line.text.length ? "\u2588" : "";

    if (line.speaker === "system") {
      return (
        <div
          key={`${sceneIdx}-${lineIdx}`}
          className="mt-1 text-[11px]"
          style={{ color: "rgba(255,255,255,0.25)" }}
        >
          {text}{cursor}
        </div>
      );
    }

    const color = line.speaker === "you" ? "#60a5fa" : "#a78bfa";
    return (
      <div key={`${sceneIdx}-${lineIdx}`} className="mt-2">
        <span style={{ color }}>{line.speaker}:</span>{" "}
        <span>{text}{cursor}</span>
      </div>
    );
  }

  return (
    <section className="max-w-6xl mx-auto px-6 pt-28 pb-24">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
        {/* Left: copy */}
        <div>
          <h1
            className="text-[48px] md:text-[64px] font-normal tracking-tight leading-[1.0] mb-6"
            style={{
              fontFamily: "var(--font-serif)",
              animation: "drift-up 400ms ease 50ms both",
            }}
          >
            Persistent memory
            <br />
            for Claude.
          </h1>

          <p
            className="text-[18px] leading-[1.6] mb-10 max-w-lg"
            style={{
              color: "var(--muted)",
              animation: "drift-up 400ms ease 100ms both",
            }}
          >
            Claude forgets everything between sessions. CMK fixes that.
            Your preferences, decisions, and context persist across
            every conversation.
          </p>

          <div
            className="flex flex-col sm:flex-row items-start gap-3"
            style={{ animation: "drift-up 400ms ease 150ms both" }}
          >
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
              Get started free
            </Link>
            <Link
              href="/docs"
              className="px-6 py-3 rounded-[var(--radius)] text-[15px] font-medium"
              style={{
                background: "transparent",
                border: "1px solid var(--border)",
                color: "var(--foreground)",
                transition: "background 140ms ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "var(--surface-hover)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
              }}
            >
              Read the docs
            </Link>
          </div>
        </div>

        {/* Right: animated terminal */}
        <div style={{ animation: "drift-up 500ms ease 200ms both" }}>
          <div
            className="rounded-[var(--radius-lg)] overflow-hidden"
            style={{
              border: "1px solid var(--border)",
              boxShadow: "var(--shadow-md)",
            }}
          >
            {/* Terminal header */}
            <div
              className="flex items-center gap-2 px-4 py-3"
              style={{
                background: "var(--code-bg)",
                borderBottom: "1px solid rgba(255,255,255,0.06)",
              }}
            >
              <div className="flex gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#ef4444" }} />
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#eab308" }} />
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#22c55e" }} />
              </div>
              <span
                className="ml-2 text-[12px] font-mono"
                style={{ color: "rgba(255,255,255,0.35)" }}
              >
                {SCENES[currentScene]?.label ?? "session 1"}
              </span>
            </div>

            {/* Terminal body */}
            <div
              ref={containerRef}
              className="px-5 py-5 font-mono text-[13px] leading-[1.7] overflow-y-auto"
              style={{
                background: "var(--code-bg)",
                color: "var(--code-fg)",
                height: "320px",
              }}
            >
              {SCENES.map((scene, si) => {
                const sceneLines = visibleLines.filter((l) => l.sceneIdx === si);
                if (sceneLines.length === 0) return null;

                return (
                  <div key={si}>
                    {si > 0 && (
                      <div
                        className="mt-4 mb-3 text-[11px] text-center"
                        style={{
                          color: "rgba(255,255,255,0.2)",
                          borderTop: "1px solid rgba(255,255,255,0.06)",
                          paddingTop: "12px",
                        }}
                      >
                        {scene.label}
                      </div>
                    )}
                    {sceneLines.map((vl) =>
                      renderLine(si, vl.lineIdx, scene.lines[vl.lineIdx], vl.chars)
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Feature strip */}
      <div
        className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-16"
        style={{ animation: "drift-up 500ms ease 300ms both" }}
      >
        {FEATURES.map((f) => (
          <div
            key={f.label}
            className="px-5 py-4 rounded-[var(--radius)]"
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border-light)",
            }}
          >
            <div
              className="text-[14px] font-medium mb-1"
              style={{ color: "var(--foreground)" }}
            >
              {f.label}
            </div>
            <div
              className="text-[13px]"
              style={{ color: "var(--muted)" }}
            >
              {f.detail}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
