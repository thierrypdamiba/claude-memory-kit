export function IdentityPreview() {
  return (
    <section className="max-w-4xl mx-auto px-6 py-20">
      <h2
        className="text-[32px] font-normal tracking-tight mb-2"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        A living identity document
      </h2>
      <p
        className="text-[15px] leading-[1.6] mb-10"
        style={{ color: "var(--muted)" }}
      >
        CMK builds a synthesis of who you are as a developer. Updated
        automatically, always editable.
      </p>

      {/* Identity card */}
      <div
        className="max-w-2xl mx-auto rounded-[var(--radius-lg)] p-8 md:p-10"
        style={{
          background: "var(--warm-paper)",
          border: "1px solid var(--border-light)",
          boxShadow: "var(--shadow-md)",
          animation: "drift-up 400ms ease both",
        }}
      >
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-[13px] font-medium"
            style={{
              background: "rgba(192, 86, 33, 0.1)",
              color: "var(--accent)",
            }}
          >
            ID
          </div>
          <div>
            <p
              className="text-[11px] font-medium uppercase tracking-wider"
              style={{ color: "var(--sage)" }}
            >
              Identity synthesis
            </p>
            <p
              className="text-[12px]"
              style={{ color: "var(--muted-light)" }}
            >
              Last updated 2 hours ago
            </p>
          </div>
        </div>

        {/* Identity text */}
        <div
          className="text-[16px] leading-[1.8] space-y-4"
          style={{
            fontFamily: "var(--font-serif)",
            color: "var(--foreground)",
          }}
        >
          <p>
            You are a senior TypeScript developer who works primarily with
            Next.js and PostgreSQL. You prefer functional patterns over
            class-based code and favor explicit types over inference when the
            type is not immediately obvious.
          </p>
          <p>
            Your code style leans minimal: short variable names in tight
            scopes, descriptive names at module boundaries. You use Tailwind
            for styling and prefer inline styles with CSS variables for design
            tokens.
          </p>
          <p>
            You work on a team of five. Sarah handles auth, Marcus owns the
            data pipeline, and you lead the frontend and API integration
            layer.
          </p>
        </div>

        {/* Bottom metadata */}
        <div
          className="mt-6 pt-4 flex items-center gap-3"
          style={{ borderTop: "1px solid var(--border)" }}
        >
          <span
            className="px-2 py-1 rounded-[4px] text-[11px] font-medium"
            style={{
              background: "rgba(217, 119, 6, 0.1)",
              color: "var(--gate-behavioral)",
            }}
          >
            12 behavioral
          </span>
          <span
            className="px-2 py-1 rounded-[4px] text-[11px] font-medium"
            style={{
              background: "rgba(37, 99, 235, 0.1)",
              color: "var(--gate-relational)",
            }}
          >
            5 relational
          </span>
          <span
            className="px-2 py-1 rounded-[4px] text-[11px] font-medium"
            style={{
              background: "rgba(124, 58, 237, 0.1)",
              color: "var(--gate-epistemic)",
            }}
          >
            8 epistemic
          </span>
        </div>
      </div>
    </section>
  );
}
