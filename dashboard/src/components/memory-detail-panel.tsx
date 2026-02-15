"use client";

import { useEffect, useState } from "react";
import { api, type Memory, type RelatedNode } from "@/lib/api";
import { GateBadge } from "./gate-badge";

interface Props {
  memory: Memory;
  onClose: () => void;
  onForget?: (id: string) => void;
  onUpdate?: (id: string, updates: Partial<Memory>) => void;
}

export function MemoryDetailPanel({ memory, onClose, onForget, onUpdate }: Props) {
  const [related, setRelated] = useState<RelatedNode[]>([]);
  const [forgetting, setForgetting] = useState(false);
  const [pinning, setPinning] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState(memory.content);

  useEffect(() => {
    setEditContent(memory.content);
    setEditing(false);
    setPinned(false);
    api
      .graph(memory.id)
      .then((res) => setRelated(res.related))
      .catch(() => {});
  }, [memory.id, memory.content]);

  const handleForget = async () => {
    setForgetting(true);
    try {
      await api.forget(memory.id, "deleted from detail panel");
      onForget?.(memory.id);
      onClose();
    } catch {
      setForgetting(false);
    }
  };

  const handlePin = async () => {
    setPinning(true);
    try {
      if (pinned) {
        await api.unpin(memory.id);
        setPinned(false);
      } else {
        await api.pin(memory.id);
        setPinned(true);
      }
    } catch {
      // ignore
    } finally {
      setPinning(false);
    }
  };

  const handleSaveEdit = async () => {
    if (editContent === memory.content) {
      setEditing(false);
      return;
    }
    try {
      await api.updateMemory(memory.id, { content: editContent });
      onUpdate?.(memory.id, { content: editContent });
      setEditing(false);
    } catch {
      // ignore
    }
  };

  return (
    <div
      className="w-80 shrink-0 h-full overflow-y-auto"
      style={{
        borderLeft: "1px solid var(--border-light)",
        background: "var(--surface)",
        animation: "drift-up 140ms ease",
      }}
    >
      <div className="p-5">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <GateBadge gate={memory.gate} />
          <button
            onClick={onClose}
            className="w-6 h-6 flex items-center justify-center rounded-[4px] text-[16px]"
            style={{ color: "var(--muted)" }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "var(--surface-hover)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "transparent";
            }}
          >
            &times;
          </button>
        </div>

        {/* Content */}
        {editing ? (
          <div className="mb-5">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full text-[14px] leading-[1.6] p-3 rounded-[var(--radius-sm)] outline-none resize-none min-h-[100px]"
              style={{
                background: "var(--warm-paper)",
                border: "1px solid var(--border)",
                color: "var(--foreground)",
                fontFamily: "var(--font-serif)",
              }}
            />
            <div className="flex gap-2 mt-2">
              <button
                onClick={handleSaveEdit}
                className="px-3 py-1.5 rounded-[var(--radius-sm)] text-[12px] font-medium"
                style={{
                  background: "var(--foreground)",
                  color: "var(--background)",
                }}
              >
                Save
              </button>
              <button
                onClick={() => {
                  setEditContent(memory.content);
                  setEditing(false);
                }}
                className="px-3 py-1.5 rounded-[var(--radius-sm)] text-[12px] font-medium"
                style={{
                  background: "var(--warm-paper)",
                  border: "1px solid var(--border-light)",
                  color: "var(--muted)",
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div
            className="text-[14px] leading-[1.6] mb-5"
            style={{ fontFamily: "var(--font-serif)" }}
          >
            {memory.content}
          </div>
        )}

        {/* Metadata */}
        <div className="space-y-2 mb-5">
          <MetaRow label="Gate" value={memory.gate} />
          {memory.person && (
            <MetaRow label="Person" value={memory.person} />
          )}
          {memory.project && (
            <MetaRow label="Project" value={memory.project} />
          )}
          <MetaRow
            label="Confidence"
            value={`${(memory.confidence * 100).toFixed(0)}%`}
          />
          <MetaRow
            label="Accessed"
            value={`${memory.access_count}x`}
          />
          <MetaRow label="Decay" value={memory.decay_class} />
          <MetaRow
            label="Created"
            value={new Date(memory.created).toLocaleString()}
          />
          <MetaRow
            label="Last accessed"
            value={new Date(memory.last_accessed).toLocaleString()}
          />
        </div>

        {/* Related memories */}
        {related.length > 0 && (
          <div className="mb-5">
            <p
              className="text-[12px] font-medium uppercase tracking-wider mb-2"
              style={{ color: "var(--sage)" }}
            >
              Related
            </p>
            <div className="space-y-2">
              {related.map((r) => (
                <div
                  key={r.id}
                  className="rounded-[var(--radius-sm)] p-2.5 text-[13px]"
                  style={{
                    background: "var(--warm-paper)",
                    border: "1px solid var(--border-light)",
                  }}
                >
                  <p
                    className="text-[12px] mb-1"
                    style={{ color: "var(--dust)" }}
                  >
                    {r.relation}
                  </p>
                  <p className="line-clamp-2">{r.preview}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div
          className="pt-4 space-y-2"
          style={{ borderTop: "1px solid var(--border-light)" }}
        >
          <button
            onClick={handleForget}
            disabled={forgetting}
            className="w-full px-3 py-2 rounded-[var(--radius-sm)] text-[13px] font-medium text-left"
            style={{
              color: "var(--gate-correction)",
              background: "rgba(220, 38, 38, 0.04)",
              border: "1px solid rgba(220, 38, 38, 0.1)",
              opacity: forgetting ? 0.5 : 1,
            }}
          >
            {forgetting ? "Forgetting..." : "Forget this memory"}
          </button>
          <button
            onClick={handlePin}
            disabled={pinning}
            className="w-full px-3 py-2 rounded-[var(--radius-sm)] text-[13px] font-medium text-left"
            style={{
              color: pinned ? "var(--gate-promissory)" : "var(--muted)",
              background: pinned
                ? "rgba(5, 150, 105, 0.06)"
                : "var(--warm-paper)",
              border: pinned
                ? "1px solid rgba(5, 150, 105, 0.15)"
                : "1px solid var(--border-light)",
              opacity: pinning ? 0.5 : 1,
            }}
          >
            {pinning ? "..." : pinned ? "Unpin this memory" : "Pin this memory"}
          </button>
          <button
            onClick={() => setEditing(true)}
            disabled={editing}
            className="w-full px-3 py-2 rounded-[var(--radius-sm)] text-[13px] font-medium text-left"
            style={{
              color: "var(--muted)",
              background: "var(--warm-paper)",
              border: "1px solid var(--border-light)",
              opacity: editing ? 0.5 : 1,
            }}
          >
            Edit content
          </button>
        </div>

        {/* Full ID */}
        <p
          className="font-mono text-[11px] mt-5 pt-3"
          style={{
            color: "var(--dust)",
            borderTop: "1px solid var(--border-light)",
            wordBreak: "break-all",
          }}
        >
          {memory.id}
        </p>
      </div>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-[13px]">
      <span style={{ color: "var(--muted)" }}>{label}</span>
      <span style={{ color: "var(--foreground)" }}>{value}</span>
    </div>
  );
}
