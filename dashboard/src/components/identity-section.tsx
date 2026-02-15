"use client";

import { useState } from "react";

interface Props {
  title: string;
  content: string;
  gate?: string;
  memoryCount?: number;
  onSave?: (content: string) => void;
  locked?: boolean;
}

export function IdentitySection({
  title,
  content,
  gate,
  memoryCount,
  onSave,
  locked = false,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState(content);

  const handleSave = () => {
    onSave?.(editContent);
    setEditing(false);
  };

  const gateColor = gate ? `var(--gate-${gate})` : "var(--sage)";

  return (
    <div
      className="rounded-[var(--radius)] p-5 mb-3"
      style={{
        background: "var(--warm-paper)",
        border: "1px solid var(--border-light)",
        boxShadow: "var(--shadow-xs)",
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span
            className="w-1 h-4 rounded-full"
            style={{ background: gateColor }}
          />
          <h4 className="text-[14px] font-medium">{title}</h4>
        </div>
        <div className="flex items-center gap-2">
          {memoryCount !== undefined && (
            <span
              className="text-[12px]"
              style={{ color: "var(--dust)" }}
            >
              {memoryCount} memories
            </span>
          )}
          {!locked && onSave && (
            <button
              onClick={() => {
                if (editing) handleSave();
                else setEditing(true);
              }}
              className="text-[12px] font-medium"
              style={{ color: "var(--accent)" }}
            >
              {editing ? "Save" : "Edit"}
            </button>
          )}
          {locked && (
            <span
              className="text-[11px]"
              style={{ color: "var(--dust)" }}
            >
              locked
            </span>
          )}
        </div>
      </div>

      {editing ? (
        <textarea
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
          className="w-full text-[14px] leading-[1.6] p-3 rounded-[var(--radius-sm)] outline-none resize-none min-h-[80px]"
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            color: "var(--foreground)",
            fontFamily: "var(--font-serif)",
          }}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = "var(--accent)";
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = "var(--border)";
          }}
        />
      ) : (
        <div
          className="text-[14px] leading-[1.6] whitespace-pre-wrap"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          {content}
        </div>
      )}
    </div>
  );
}
