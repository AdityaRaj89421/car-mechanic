"use client";

/**
 * app/error.tsx — Next.js route-level error boundary.
 *
 * Catches rendering errors within the page (React component crashes).
 * Shown instead of a blank screen when something goes wrong at runtime.
 *
 * Does NOT catch async data-fetching errors — those are handled by
 * the useChat hook's error state and displayed as inline banners.
 */

import { useEffect, useState } from "react";
import { AlertTriangle, RefreshCw, WifiOff } from "lucide-react";
import { checkHealth } from "@/lib/api";

interface Props {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: Props) {
  const [backendUp, setBackendUp] = useState<boolean | null>(null);

  // Check if the backend is the problem on mount
  useEffect(() => {
    checkHealth().then(setBackendUp);
  }, []);

  // Log to console for debugging
  useEffect(() => {
    console.error("[AI Car Mechanic] Page error:", error);
  }, [error]);

  const isBackendDown = backendUp === false;

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-6">
      <div className="max-w-md w-full text-center space-y-6">
        {/* Icon */}
        <div className="flex justify-center">
          <div
            className={`p-5 rounded-2xl ${
              isBackendDown
                ? "bg-orange-500/15 border border-orange-500/30"
                : "bg-red-500/15 border border-red-500/30"
            }`}
          >
            {isBackendDown ? (
              <WifiOff className="w-10 h-10 text-orange-400" />
            ) : (
              <AlertTriangle className="w-10 h-10 text-red-400" />
            )}
          </div>
        </div>

        {/* Title */}
        <div className="space-y-2">
          <h1 className="text-xl font-bold text-white">
            {isBackendDown ? "Backend Unavailable" : "Something went wrong"}
          </h1>
          <p className="text-sm text-slate-400 leading-relaxed">
            {isBackendDown ? (
              <>
                The AI Car Mechanic server isn&apos;t responding.
                <br />
                Make sure the Django backend is running on{" "}
                <code className="text-orange-400 text-xs bg-slate-800 px-1.5 py-0.5 rounded">
                  {process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}
                </code>
              </>
            ) : (
              <>
                An unexpected error occurred in the app.
                {error.message && (
                  <span className="block mt-2 text-xs text-slate-500 font-mono bg-slate-900 px-3 py-2 rounded-lg border border-slate-800">
                    {error.message}
                  </span>
                )}
              </>
            )}
          </p>
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-3">
          <button
            onClick={reset}
            className="
              flex items-center justify-center gap-2
              px-6 py-3 rounded-xl font-medium text-sm text-white
              bg-blue-600 hover:bg-blue-500 transition-colors cursor-pointer
            "
          >
            <RefreshCw className="w-4 h-4" />
            Try again
          </button>

          {isBackendDown && (
            <button
              onClick={() => checkHealth().then(setBackendUp)}
              className="
                flex items-center justify-center gap-2
                px-6 py-3 rounded-xl font-medium text-sm
                text-slate-300 bg-slate-800 hover:bg-slate-700
                border border-slate-700 transition-colors cursor-pointer
              "
            >
              Check connection
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
