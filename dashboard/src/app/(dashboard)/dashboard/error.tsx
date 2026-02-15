"use client";

import { useEffect } from "react";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Dashboard error:", error);
  }, [error]);

  return (
    <div className="flex flex-1 items-center justify-center py-20">
      <div className="text-center" style={{ maxWidth: 420 }}>
        <h2
          className="text-lg font-semibold mb-2"
          style={{ letterSpacing: "-0.015em" }}
        >
          Something went wrong
        </h2>
        <p
          className="text-sm mb-6"
          style={{ color: "var(--muted)", lineHeight: 1.5 }}
        >
          There was a problem loading this page. Try again or go back to the
          dashboard.
        </p>
        <button
          onClick={reset}
          className="px-5 py-2 text-sm font-medium text-white rounded-md cursor-pointer"
          style={{
            background: "var(--accent)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          Try again
        </button>
      </div>
    </div>
  );
}
