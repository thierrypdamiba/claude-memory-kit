"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { api, type Memory, type RelatedNode } from "@/lib/api";
import { GateBadge } from "@/components/gate-badge";

interface GraphNode {
  id: string;
  label: string;
  gate: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
}

interface GraphEdge {
  from: string;
  to: string;
  relation: string;
}

const GATE_COLORS: Record<string, string> = {
  behavioral: "#f59e0b",
  relational: "#3b82f6",
  epistemic: "#8b5cf6",
  promissory: "#10b981",
  correction: "#ef4444",
};

export default function GraphPage() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [selected, setSelected] = useState<Memory | null>(null);
  const [loading, setLoading] = useState(true);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const nodesRef = useRef<GraphNode[]>([]);

  useEffect(() => {
    api
      .memories(100)
      .then(async (res) => {
        setMemories(res.memories);
        const gn: GraphNode[] = res.memories.map((m, i) => ({
          id: m.id,
          label: m.content.slice(0, 40),
          gate: m.gate,
          x: 400 + Math.cos(i * 0.8) * (150 + i * 10),
          y: 300 + Math.sin(i * 0.8) * (150 + i * 10),
          vx: 0,
          vy: 0,
        }));
        setNodes(gn);
        nodesRef.current = gn;

        const allEdges: GraphEdge[] = [];
        for (const m of res.memories.slice(0, 20)) {
          try {
            const g = await api.graph(m.id);
            for (const rel of g.related) {
              const exists = allEdges.some(
                (e) =>
                  (e.from === m.id && e.to === rel.id) ||
                  (e.from === rel.id && e.to === m.id)
              );
              if (!exists)
                allEdges.push({ from: m.id, to: rel.id, relation: rel.relation });
            }
          } catch {}
        }
        setEdges(allEdges);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const ns = nodesRef.current;
    if (!canvas || ns.length === 0) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = canvas.offsetWidth * 2;
    canvas.height = canvas.offsetHeight * 2;
    ctx.scale(2, 2);
    ctx.clearRect(0, 0, canvas.offsetWidth, canvas.offsetHeight);

    // Repulsion
    for (const node of ns) {
      for (const other of ns) {
        if (node === other) continue;
        const dx = node.x - other.x;
        const dy = node.y - other.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = 500 / (dist * dist);
        node.vx += (dx / dist) * force;
        node.vy += (dy / dist) * force;
      }
      node.vx += (canvas.offsetWidth / 2 - node.x) * 0.001;
      node.vy += (canvas.offsetHeight / 2 - node.y) * 0.001;
      node.vx *= 0.9;
      node.vy *= 0.9;
      node.x += node.vx;
      node.y += node.vy;
    }

    // Spring forces
    for (const edge of edges) {
      const a = ns.find((n) => n.id === edge.from);
      const b = ns.find((n) => n.id === edge.to);
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = (dist - 120) * 0.005;
      a.vx += (dx / dist) * force;
      a.vy += (dy / dist) * force;
      b.vx -= (dx / dist) * force;
      b.vy -= (dy / dist) * force;
    }

    // Draw edges
    ctx.lineWidth = 1;
    for (const edge of edges) {
      const a = ns.find((n) => n.id === edge.from);
      const b = ns.find((n) => n.id === edge.to);
      if (!a || !b) continue;
      ctx.strokeStyle = "rgba(0,0,0,0.06)";
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    // Draw nodes
    for (const node of ns) {
      const color = GATE_COLORS[node.gate] || "#999";
      const isSel = selected?.id === node.id;

      // Glow for selected
      if (isSel) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, 16, 0, Math.PI * 2);
        ctx.fillStyle = color + "15";
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(node.x, node.y, isSel ? 7 : 4.5, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();

      if (isSel) {
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }

    animRef.current = requestAnimationFrame(draw);
  }, [edges, selected]);

  useEffect(() => {
    if (nodesRef.current.length > 0) {
      animRef.current = requestAnimationFrame(draw);
    }
    return () => cancelAnimationFrame(animRef.current);
  }, [draw, nodes.length]);

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    for (const node of nodesRef.current) {
      const dx = node.x - mx;
      const dy = node.y - my;
      if (dx * dx + dy * dy < 200) {
        setSelected(memories.find((m) => m.id === node.id) || null);
        return;
      }
    }
    setSelected(null);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-3">
          <div
            className="w-5 h-5 rounded-full border-2 animate-spin"
            style={{
              borderColor: "var(--border)",
              borderTopColor: "var(--accent)",
            }}
          />
          <p className="text-[14px]" style={{ color: "var(--muted)" }}>
            Building graph...
          </p>
        </div>
      </div>
    );
  }

  if (nodes.length === 0) {
    return (
      <div>
        <h2 className="text-[20px] font-semibold tracking-tight mb-6">
          Memory Graph
        </h2>
        <div className="flex flex-col items-center justify-center h-64 gap-3">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center text-lg"
            style={{ background: "var(--surface-hover)", color: "var(--muted)" }}
          >
            &#9673;
          </div>
          <p className="text-[14px]" style={{ color: "var(--muted)" }}>
            No memories to visualize yet.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-[20px] font-semibold tracking-tight mb-6">
        Memory Graph
      </h2>
      <div className="flex gap-4">
        <div
          className="flex-1 rounded-[var(--radius)] overflow-hidden"
          style={{
            border: "1px solid var(--border-light)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <canvas
            ref={canvasRef}
            onClick={handleClick}
            className="w-full cursor-crosshair"
            style={{ height: 500, background: "var(--surface)" }}
          />
        </div>
        {selected && (
          <div
            className="w-72 p-5 rounded-[var(--radius)] shrink-0"
            style={{
              background: "var(--warm-paper)",
              border: "1px solid var(--border-light)",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            <GateBadge gate={selected.gate} />
            <p
              className="text-[14px] mt-3 leading-[1.4]"
              style={{ fontFamily: "var(--font-serif)" }}
            >
              {selected.content}
            </p>
            <div
              className="mt-4 space-y-1.5 text-[13px]"
              style={{ color: "var(--muted)" }}
            >
              {selected.person && <p>Person: {selected.person}</p>}
              {selected.project && <p>Project: {selected.project}</p>}
              <p>Confidence: {(selected.confidence * 100).toFixed(0)}%</p>
              <p>Accessed: {selected.access_count}x</p>
              <p
                className="font-mono text-[11px] mt-3 pt-3"
                style={{
                  color: "var(--dust)",
                  borderTop: "1px solid var(--border-light)",
                }}
              >
                {selected.id}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex gap-4 mt-4">
        {Object.entries(GATE_COLORS).map(([gate, color]) => (
          <div
            key={gate}
            className="flex items-center gap-1.5 text-[12px]"
            style={{ color: "var(--sage)" }}
          >
            <span
              className="w-2 h-2 rounded-full inline-block"
              style={{ background: color }}
            />
            {gate}
          </div>
        ))}
      </div>
    </div>
  );
}
