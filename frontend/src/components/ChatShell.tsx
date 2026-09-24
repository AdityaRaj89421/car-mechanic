"use client";

/**
 * ChatShell — Main chat interface shell for AI Car Mechanic.
 *
 * Stage 1: Layout and UI only. All buttons are non-functional placeholders.
 * Stage 2 will add: message state, API calls, streaming responses, media previews.
 */

import { useState, useRef } from "react";
import { ImageIcon, MicIcon, VideoIcon, SendIcon, CarIcon } from "lucide-react";

/** Shape of a single chat message (will be expanded in Stage 2). */
interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

/** Placeholder empty-state shown when there are no messages yet. */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center flex-1 gap-4 text-center px-6">
      <div className="w-16 h-16 rounded-2xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center">
        <CarIcon className="w-8 h-8 text-blue-400" />
      </div>
      <div>
        <h2 className="text-xl font-semibold text-gray-100 mb-2">
          AI Car Mechanic
        </h2>
        <p className="text-gray-400 text-sm max-w-sm leading-relaxed">
          Describe your car problem in text, or attach an image, audio
          recording, or video. I&apos;ll diagnose the issue and help you book a
          service.
        </p>
      </div>
      <div className="flex flex-wrap gap-2 justify-center mt-2">
        {[
          "My engine makes a clicking noise",
          "Check engine light is on",
          "Car won't start in cold weather",
        ].map((prompt) => (
          <button
            key={prompt}
            type="button"
            aria-label={`Example prompt: ${prompt}`}
            className="px-3 py-1.5 rounded-full border border-gray-700 text-gray-400 text-xs hover:border-blue-500 hover:text-blue-400 transition-colors"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}

/** A single rendered chat message bubble. */
function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
      role="listitem"
    >
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold
          ${isUser ? "bg-blue-600 text-white" : "bg-gray-700 text-gray-300"}`}
        aria-hidden="true"
      >
        {isUser ? "U" : "AI"}
      </div>
      {/* Bubble */}
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed
          ${isUser
            ? "bg-blue-600 text-white rounded-tr-sm"
            : "bg-gray-800 text-gray-100 rounded-tl-sm"
          }`}
      >
        {message.content}
      </div>
    </div>
  );
}

/** Main chat shell component. */
export default function ChatShell() {
  const [messages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  /** Placeholder send handler — Stage 2 will call POST /api/chat/. */
  function handleSend() {
    if (!inputValue.trim()) return;
    // TODO Stage 2: dispatch message to API and append to messages list
    setInputValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  /** Auto-grow textarea height as the user types. */
  function handleTextareaChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInputValue(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="flex items-center gap-3 px-6 py-4 border-b border-gray-800 flex-shrink-0">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
          <CarIcon className="w-4 h-4 text-white" />
        </div>
        <div>
          <h1 className="text-sm font-semibold text-gray-100">AI Car Mechanic</h1>
          <p className="text-xs text-gray-500">Powered by Gemini</p>
        </div>
      </header>

      {/* ── Message list ───────────────────────────────────────────────── */}
      <main
        className="flex-1 overflow-y-auto px-6 py-4"
        aria-label="Chat messages"
      >
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          <ol className="flex flex-col gap-4" aria-label="Conversation">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
          </ol>
        )}
      </main>

      {/* ── Input bar ──────────────────────────────────────────────────── */}
      <footer className="px-6 py-4 border-t border-gray-800 flex-shrink-0">
        <div className="flex items-end gap-2 bg-gray-900 border border-gray-700 rounded-2xl px-4 py-3 focus-within:border-blue-500 transition-colors">
          {/* Attach buttons */}
          <div className="flex gap-1 flex-shrink-0 pb-0.5">
            <button
              type="button"
              id="attach-image-btn"
              aria-label="Attach image (coming soon)"
              title="Attach image (coming soon)"
              disabled
              className="p-1.5 rounded-lg text-gray-500 hover:text-gray-400 hover:bg-gray-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ImageIcon className="w-4 h-4" />
            </button>
            <button
              type="button"
              id="attach-audio-btn"
              aria-label="Attach audio (coming soon)"
              title="Attach audio (coming soon)"
              disabled
              className="p-1.5 rounded-lg text-gray-500 hover:text-gray-400 hover:bg-gray-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <MicIcon className="w-4 h-4" />
            </button>
            <button
              type="button"
              id="attach-video-btn"
              aria-label="Attach video (coming soon)"
              title="Attach video (coming soon)"
              disabled
              className="p-1.5 rounded-lg text-gray-500 hover:text-gray-400 hover:bg-gray-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <VideoIcon className="w-4 h-4" />
            </button>
          </div>

          {/* Text input */}
          <textarea
            ref={textareaRef}
            id="chat-input"
            rows={1}
            value={inputValue}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder="Describe your car problem…"
            aria-label="Type your message"
            className="flex-1 bg-transparent text-sm text-gray-100 placeholder-gray-500 resize-none outline-none leading-relaxed max-h-40"
          />

          {/* Send button */}
          <button
            type="button"
            id="send-message-btn"
            aria-label="Send message"
            onClick={handleSend}
            disabled={!inputValue.trim()}
            className="flex-shrink-0 w-8 h-8 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-colors pb-0.5"
          >
            <SendIcon className="w-3.5 h-3.5 text-white" />
          </button>
        </div>
        <p className="text-center text-xs text-gray-600 mt-2">
          Press Enter to send · Shift+Enter for new line
        </p>
      </footer>
    </div>
  );
}
