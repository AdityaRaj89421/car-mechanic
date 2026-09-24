"use client";

/**
 * app/global-error.tsx — Top-level catastrophic error boundary.
 *
 * Catches errors that propagate past the route-level error.tsx, including
 * errors in the root layout. Must render its own <html>/<body> tags
 * because layout.tsx is bypassed.
 *
 * This is the last line of defence — a blank screen should never happen.
 */

export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          background: "#020617",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "system-ui, sans-serif",
          color: "#f1f5f9",
          padding: "24px",
        }}
      >
        <div style={{ textAlign: "center", maxWidth: "400px" }}>
          <div
            style={{
              width: "64px",
              height: "64px",
              borderRadius: "50%",
              background: "rgba(239,68,68,0.15)",
              border: "1px solid rgba(239,68,68,0.3)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 20px",
              fontSize: "28px",
            }}
          >
            🔧
          </div>
          <h1 style={{ fontSize: "18px", fontWeight: "700", marginBottom: "8px" }}>
            AI Car Mechanic — Critical Error
          </h1>
          <p style={{ fontSize: "14px", color: "#94a3b8", marginBottom: "24px", lineHeight: "1.5" }}>
            A critical error occurred and the app could not recover automatically.
            Please refresh the page or try again.
          </p>
          <button
            onClick={reset}
            style={{
              padding: "12px 28px",
              borderRadius: "10px",
              background: "#2563eb",
              color: "white",
              fontWeight: "600",
              fontSize: "14px",
              border: "none",
              cursor: "pointer",
            }}
          >
            Reload app
          </button>
        </div>
      </body>
    </html>
  );
}
