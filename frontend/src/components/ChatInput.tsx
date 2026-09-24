"use client";

import { useRef, type KeyboardEvent } from "react";
import { Send, Image as ImageIcon, Mic, Video, Loader2, X } from "lucide-react";

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  onUpload: (file: File, type: "image" | "audio" | "video") => void;
  isLoading: boolean;
  uploadProgress: number | null;
  disabled: boolean;
}

const ACCEPT: Record<"image" | "audio" | "video", string> = {
  image: "image/jpeg,image/png,image/webp",
  audio: "audio/mpeg,audio/wav,audio/m4a",
  video: "video/mp4,video/quicktime",
};

/**
 * ChatInput — the bottom input bar.
 * Handles text submission (Enter / Shift+Enter), and media file selection
 * for image, audio, and video uploads.
 */
export function ChatInput({
  value,
  onChange,
  onSend,
  onUpload,
  isLoading,
  uploadProgress,
  disabled,
}: Props) {
  const imageRef = useRef<HTMLInputElement>(null);
  const audioRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLInputElement>(null);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading && value.trim()) onSend();
    }
  };

  const handleFileChange =
    (type: "image" | "audio" | "video") =>
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onUpload(file, type);
      e.target.value = ""; // reset so same file can be re-selected
    };

  const isUploading = uploadProgress !== null;
  const busy = isLoading || isUploading || disabled;

  return (
    <div className="px-4 pb-4 pt-2">
      {/* Upload progress bar */}
      {isUploading && (
        <div className="mb-2 h-1 w-full rounded-full bg-slate-700 overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-200 rounded-full"
            style={{ width: `${uploadProgress ?? 0}%` }}
          />
        </div>
      )}

      <div className="flex items-end gap-2 rounded-2xl border border-slate-700/60 bg-slate-800/80 px-3 py-2 shadow-lg backdrop-blur-sm focus-within:border-blue-500/50 transition-colors">
        {/* Attachment buttons */}
        <div className="flex gap-1 pb-1">
          <UploadTrigger
            id="upload-image-btn"
            icon={<ImageIcon className="w-4 h-4" />}
            label="Attach image"
            onClick={() => imageRef.current?.click()}
            disabled={busy}
            title="Upload image (JPEG/PNG/WebP ≤5 MB)"
          />
          <UploadTrigger
            id="upload-audio-btn"
            icon={<Mic className="w-4 h-4" />}
            label="Attach audio"
            onClick={() => audioRef.current?.click()}
            disabled={busy}
            title="Upload audio (MP3/WAV/M4A ≤10 MB)"
          />
          <UploadTrigger
            id="upload-video-btn"
            icon={<Video className="w-4 h-4" />}
            label="Attach video"
            onClick={() => videoRef.current?.click()}
            disabled={busy}
            title="Upload video (MP4/MOV ≤25 MB)"
          />
        </div>

        {/* Text area */}
        <textarea
          id="chat-input"
          rows={1}
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            // auto-grow
            e.target.style.height = "auto";
            e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
          }}
          onKeyDown={handleKeyDown}
          placeholder={isUploading ? `Uploading… ${uploadProgress}%` : "Describe your car issue…"}
          disabled={busy}
          className="
            flex-1 bg-transparent resize-none text-sm text-white
            placeholder-slate-500 outline-none leading-relaxed
            disabled:opacity-50 min-h-[36px] max-h-40 py-1.5
          "
        />

        {/* Send button */}
        <button
          id="chat-send-btn"
          onClick={onSend}
          disabled={busy || !value.trim()}
          aria-label="Send message"
          className="
            flex-shrink-0 p-2 rounded-xl mb-0.5
            bg-blue-600 hover:bg-blue-500
            disabled:bg-slate-700 disabled:text-slate-500
            text-white transition-all duration-150
            hover:scale-105 active:scale-95 cursor-pointer
            disabled:cursor-not-allowed disabled:hover:scale-100
          "
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Hidden file inputs */}
      <input ref={imageRef} type="file" accept={ACCEPT.image} className="hidden" onChange={handleFileChange("image")} />
      <input ref={audioRef} type="file" accept={ACCEPT.audio} className="hidden" onChange={handleFileChange("audio")} />
      <input ref={videoRef} type="file" accept={ACCEPT.video} className="hidden" onChange={handleFileChange("video")} />
    </div>
  );
}

// ── UploadTrigger ─────────────────────────────────────────────────────────────

function UploadTrigger({
  id,
  icon,
  label,
  onClick,
  disabled,
  title,
}: {
  id: string;
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  disabled: boolean;
  title: string;
}) {
  return (
    <button
      id={id}
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={title}
      className="
        p-1.5 rounded-lg text-slate-400
        hover:text-slate-200 hover:bg-slate-700/60
        disabled:opacity-40 disabled:cursor-not-allowed
        transition-colors cursor-pointer
      "
    >
      {icon}
    </button>
  );
}
