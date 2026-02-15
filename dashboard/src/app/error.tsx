"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Unhandled error:", error);
  }, [error]);

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "system-ui, -apple-system, sans-serif",
        background: "var(--background, #faf9f7)",
        color: "var(--foreground, #2F2B27)",
      }}
    >
      <div style={{ textAlign: "center", maxWidth: 420, padding: "0 24px" }}>
        <h2
          style={{
            fontSize: 20,
            fontWeight: 600,
            marginBottom: 8,
            letterSpacing: "-0.015em",
          }}
        >
          Something went wrong
        </h2>
        <p
          style={{
            fontSize: 14,
            color: "var(--muted, #6b6560)",
            marginBottom: 24,
            lineHeight: 1.5,
          }}
        >
          An unexpected error occurred. Try refreshing the page.
        </p>
        <button
          onClick={reset}
          style={{
            padding: "8px 20px",
            fontSize: 14,
            fontWeight: 500,
            color: "#fff",
            background: "var(--accent, #c05621)",
            border: "none",
            borderRadius: "var(--radius-sm, 6px)",
            cursor: "pointer",
          }}
        >
          Try again
        </button>
      </div>
    </div>
  );
}
