"use client";

import { useState } from "react";
import type { Memory } from "@/lib/api";
import { GateBadge } from "./gate-badge";

interface Props {
  memory: Memory;
  onClick?: (memory: Memory) => void;
  onForget?: (id: string) => void;
  showScore?: number;
}

export function MemoryCard({ memory, onClick, onForget, showScore }: Props) {
  const [copied, setCopied] = useState(false);
  const date = new Date(memory.created);
  const timeAgo = formatTimeAgo(date);

  const copyId = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(memory.id);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleForget = (e: React.MouseEvent) => {
    e.stopPropagation();
    onForget?.(memory.id);
  };

  return (
    <div
      className="rounded-[var(--radius)] p-5 mb-3 group transition-shadow"
      style={{
        background: "var(--warm-paper)",
        boxShadow: "var(--shadow-xs)",
        border: "1px solid var(--border-light)",
        transition: "box-shadow 140ms ease",
        cursor: onClick ? "pointer" : "default",
      }}
      onClick={() => onClick?.(memory)}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = "var(--shadow-sm)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = "var(--shadow-xs)";
      }}
    >
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-2">
          <GateBadge gate={memory.gate} />
          {memory.person && (
            <span className="text-[13px]" style={{ color: "var(--muted)" }}>
              {memory.person}
            </span>
          )}
          {showScore !== undefined && (
            <span
              className="text-[12px] tabular-nums font-medium ml-1"
              style={{
                color:
                  showScore > 0.8
                    ? "var(--success)"
                    : showScore > 0.5
                      ? "var(--gate-behavioral)"
                      : "var(--muted)",
              }}
            >
              {(showScore * 100).toFixed(0)}%
            </span>
          )}
        </div>
        <span
          className="text-[12px] tabular-nums"
          style={{ color: "var(--dust)" }}
        >
          {timeAgo}
        </span>
      </div>

      <p className="text-[14px] leading-[1.45] mb-3">{memory.content}</p>

      <div
        className="flex items-center gap-3 text-[12px] opacity-0 group-hover:opacity-100"
        style={{
          color: "var(--dust)",
          transform: "translateY(2px)",
          transition: "opacity 140ms ease, transform 140ms ease",
        }}
      >
        <style>{`
          .group:hover .metadata-drift { transform: translateY(0) !important; }
        `}</style>
        <span className="metadata-drift" style={{ transform: "translateY(2px)", transition: "transform 140ms ease" }}>
          {(memory.confidence * 100).toFixed(0)}% confidence
        </span>
        <span className="w-px h-3" style={{ background: "var(--border)" }} />
        <span>{memory.access_count}x accessed</span>
        {memory.project && (
          <>
            <span className="w-px h-3" style={{ background: "var(--border)" }} />
            <span>{memory.project}</span>
          </>
        )}

        {/* Hover actions */}
        <span className="ml-auto flex items-center gap-2">
          <button
            onClick={copyId}
            className="text-[11px] font-mono hover:underline"
            style={{ color: copied ? "var(--success)" : "var(--dust)" }}
          >
            {copied ? "copied" : memory.id.slice(0, 8)}
          </button>
          {onForget && (
            <>
              <span className="w-px h-3" style={{ background: "var(--border)" }} />
              <button
                onClick={handleForget}
                className="text-[11px] hover:underline"
                style={{ color: "var(--gate-correction)" }}
              >
                forget
              </button>
            </>
          )}
          {onClick && (
            <>
              <span className="w-px h-3" style={{ background: "var(--border)" }} />
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onClick(memory);
                }}
                className="text-[11px] hover:underline"
                style={{ color: "var(--accent)" }}
              >
                detail
              </button>
            </>
          )}
        </span>
      </div>
    </div>
  );
}

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
