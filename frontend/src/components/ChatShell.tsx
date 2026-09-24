"use client";

/**
 * ChatShell — the root chat orchestrator.
 *
 * Assembles: header, message list, diagnosis card, error banner,
 * chat input, booking modal, and empty state.
 */

import { useState } from "react";
import { AlertCircle, Car, RefreshCw, Wrench, X } from "lucide-react";

import { useChat } from "@/hooks/useChat";
import { MessageBubble } from "./MessageBubble";
import { DiagnosisCard } from "./DiagnosisCard";
import { BookingModal } from "./BookingModal";
import { ChatInput } from "./ChatInput";

export function ChatShell() {
  const { state, bottomRef, sendText, upload, openBooking, closeBooking, clearError, reset } =
    useChat();
  const [inputValue, setInputValue] = useState("");

  const handleSend = () => {
    if (!inputValue.trim()) return;
    sendText(inputValue.trim());
    setInputValue("");
  };

  const hasMessages = state.messages.length > 0;

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-white overflow-hidden">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="flex items-center justify-between px-5 py-4 border-b border-slate-800/80 bg-slate-900/80 backdrop-blur-md flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/20">
            <Wrench className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white leading-tight">AI Car Mechanic</h1>
            <p className="text-xs text-slate-400">Powered by Gemini</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {state.conversationId && (
            <span className="text-xs text-slate-500 bg-slate-800 px-2.5 py-1 rounded-lg border border-slate-700/50">
              #{state.conversationId}
            </span>
          )}
          <button
            id="new-conversation-btn"
            onClick={reset}
            title="Start new conversation"
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700/50 transition-colors cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* ── Error banner ────────────────────────────────────────────────── */}
      {state.error && (
        <div className="flex items-start gap-3 mx-4 mt-3 px-4 py-3 rounded-xl bg-red-950/60 border border-red-500/30 flex-shrink-0">
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-300 flex-1">{state.error}</p>
          <button
            onClick={clearError}
            className="text-red-400 hover:text-red-300 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* ── Message list ─────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1 scroll-smooth">
        {!hasMessages ? (
          <EmptyState />
        ) : (
          <>
            {state.messages.map((msg) => (
              <MessageBubble key={`${msg.id}-${msg.created_at}`} message={msg} />
            ))}

            {/* Diagnosis card — rendered after the last message */}
            {state.diagnosis && (
              <DiagnosisCard diagnosis={state.diagnosis} onBookNow={openBooking} />
            )}
          </>
        )}
        <div ref={bottomRef} />
      </div>

      {/* ── Chat input ──────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 border-t border-slate-800/60 bg-slate-900/60 backdrop-blur-md">
        <ChatInput
          value={inputValue}
          onChange={setInputValue}
          onSend={handleSend}
          onUpload={upload}
          isLoading={state.isLoading}
          uploadProgress={state.uploadProgress}
          disabled={false}
        />
        <p className="text-center text-xs text-slate-600 pb-3">
          AI responses may be inaccurate. Always consult a qualified mechanic for repairs.
        </p>
      </div>

      {/* ── Booking modal ────────────────────────────────────────────────── */}
      {state.bookingModalOpen && state.conversationId && (
        <BookingModal
          conversationId={state.conversationId}
          diagnosis={state.diagnosis}
          onClose={closeBooking}
        />
      )}
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 py-16 text-center">
      <div className="p-5 rounded-2xl bg-gradient-to-br from-blue-500/20 to-indigo-600/10 border border-blue-500/20">
        <Car className="w-12 h-12 text-blue-400" />
      </div>
      <div className="space-y-2 max-w-sm">
        <h2 className="text-lg font-semibold text-white">
          Describe your car problem
        </h2>
        <p className="text-sm text-slate-400 leading-relaxed">
          I&apos;ll ask follow-up questions to pinpoint the issue, then give you
          a diagnosis and service recommendation.
        </p>
      </div>
      <div className="grid gap-2 w-full max-w-sm">
        {EXAMPLES.map((ex) => (
          <div
            key={ex}
            className="px-4 py-3 rounded-xl border border-slate-700/50 bg-slate-800/40 text-sm text-slate-300 text-left hover:border-blue-500/40 hover:bg-slate-800/70 transition-colors cursor-default"
          >
            &quot;{ex}&quot;
          </div>
        ))}
      </div>
    </div>
  );
}

const EXAMPLES = [
  "My engine makes a knocking noise when I accelerate",
  "The car vibrates heavily above 80 km/h",
  "My brakes squeal every time I slow down",
];
