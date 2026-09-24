"use client";

import Image from "next/image";
import { LoadingDots } from "./LoadingDots";
import type { MessageData } from "@/types/chat";

interface Props {
  message: MessageData;
}

/**
 * Renders a single chat message bubble — user (right) or assistant (left).
 * Handles text, images, audio players, video players, and the thinking state.
 */
export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";
  const isThinking = message.content === "__thinking__";

  return (
    <div
      className={`flex w-full gap-3 ${isUser ? "justify-end" : "justify-start"} mb-3`}
    >
      {/* Avatar — assistant only */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-sm font-bold shadow-sm">
          🔧
        </div>
      )}

      <div className={`flex flex-col gap-1.5 max-w-[72%] ${isUser ? "items-end" : "items-start"}`}>
        {/* Media attachment */}
        {message.media_url && message.media_type === "image" && (
          <div className="rounded-2xl overflow-hidden border border-white/10 shadow-md">
            <Image
              src={message.media_url}
              alt="Uploaded car photo"
              width={300}
              height={200}
              className="object-cover"
              unoptimized
            />
          </div>
        )}

        {message.media_url && message.media_type === "audio" && (
          <audio
            controls
            src={message.media_url}
            className="max-w-xs rounded-lg"
          />
        )}

        {message.media_url && message.media_type === "video" && (
          <video
            controls
            src={message.media_url}
            className="max-w-xs rounded-2xl shadow-md"
          />
        )}

        {/* Bubble */}
        <div
          className={`
            px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm
            ${isUser
              ? "bg-blue-600 text-white rounded-br-sm"
              : "bg-slate-800 text-slate-100 border border-slate-700/50 rounded-bl-sm"
            }
          `}
        >
          {isThinking ? (
            <LoadingDots />
          ) : (
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          )}
        </div>

        {/* Timestamp */}
        {!isThinking && (
          <span className="text-xs text-slate-500">
            {new Date(message.created_at).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        )}
      </div>

      {/* Avatar — user only */}
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-slate-600 to-slate-700 flex items-center justify-center text-white text-sm font-semibold shadow-sm">
          U
        </div>
      )}
    </div>
  );
}
