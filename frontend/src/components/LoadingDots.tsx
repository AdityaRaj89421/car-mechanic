"use client";

/** Animated three-dot loading indicator shown while waiting for Gemini. */
export function LoadingDots() {
  return (
    <div className="flex items-center gap-1.5 px-1 py-1" aria-label="AI is thinking">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="block w-2 h-2 rounded-full bg-slate-400"
          style={{
            animation: "bounce-dot 1.2s ease-in-out infinite",
            animationDelay: `${i * 0.18}s`,
          }}
        />
      ))}
    </div>
  );
}
