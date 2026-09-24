/**
 * lib/api.ts — Canonical API client for the AI Car Mechanic frontend.
 *
 * This is the single place all HTTP calls to the Django backend are made.
 * To point at a different backend (staging, production), change only
 * NEXT_PUBLIC_API_BASE_URL in the environment file.
 *
 * Design contracts:
 *  - Never throws. Every function returns {data} | {error}.
 *  - Timeouts: 30 s for JSON requests, 120 s for uploads (large files).
 *  - Network failures and non-2xx responses are normalised to {error: string}.
 *  - Field-level booking errors are preserved in {fieldErrors}.
 */

import type {
  BookingData,
  BookingErrors,
  ChatResponse,
  HistoryResponse,
  UploadResponse,
} from "@/types/chat";

/** The base URL of the Django backend, configured via env. */
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// ── Timeout constants ─────────────────────────────────────────────────────────

/** Default request timeout for JSON (chat, history, booking) calls. */
const JSON_TIMEOUT_MS = 30_000;

/** Extended timeout for media uploads (up to 25 MB video). */
const UPLOAD_TIMEOUT_MS = 120_000;

// ── Generic helpers ───────────────────────────────────────────────────────────

/**
 * Make a timed fetch — aborts and rejects after `ms` milliseconds.
 * The rejection message is user-friendly so it can be shown directly.
 */
async function timedFetch(
  input: RequestInfo | URL,
  init: RequestInit,
  ms: number
): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), ms);
  try {
    return await fetch(input, { ...init, signal: ctrl.signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Request timed out. The server took too long to respond.");
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

async function postJson<T>(
  path: string,
  body: Record<string, unknown>
): Promise<{ data: T } | { error: string; fieldErrors?: BookingErrors }> {
  try {
    const res = await timedFetch(
      `${API_BASE}${path}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(body),
      },
      JSON_TIMEOUT_MS
    );
    const json = await res.json();
    if (!res.ok) {
      return { error: extractError(json), fieldErrors: json as BookingErrors };
    }
    return { data: json as T };
  } catch (err) {
    return { error: networkError(err) };
  }
}

async function getJson<T>(
  path: string
): Promise<{ data: T } | { error: string }> {
  try {
    const res = await timedFetch(
      `${API_BASE}${path}`,
      { headers: { Accept: "application/json" } },
      JSON_TIMEOUT_MS
    );
    const json = await res.json();
    if (!res.ok) return { error: extractError(json) };
    return { data: json as T };
  } catch (err) {
    return { error: networkError(err) };
  }
}

function extractError(json: unknown): string {
  if (typeof json === "object" && json !== null) {
    const obj = json as Record<string, unknown>;
    if (typeof obj.detail === "string") return obj.detail;
    const msgs = Object.values(obj)
      .flat()
      .filter((v): v is string => typeof v === "string");
    if (msgs.length) return msgs[0];
  }
  return "An unexpected error occurred.";
}

function networkError(err: unknown): string {
  if (err instanceof Error) {
    // Surface timeout messages directly
    if (err.message.startsWith("Request timed out")) return err.message;
    if (err.message.includes("fetch")) {
      return "Cannot reach the server. Check that the backend is running.";
    }
    return `Network error: ${err.message}`;
  }
  return "Network error: could not reach the server.";
}

// ── Health check ──────────────────────────────────────────────────────────────

/**
 * Lightweight check: HEAD /api/chat/ — resolves true if the backend is up.
 * Used by the error boundary to distinguish "backend down" from "JS error".
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const ctrl = new AbortController();
    setTimeout(() => ctrl.abort(), 5_000);
    const res = await fetch(`${API_BASE}/api/chat/`, {
      method: "HEAD",
      signal: ctrl.signal,
    });
    // Any HTTP response (even 405 Method Not Allowed) means server is up
    return res.status < 500;
  } catch {
    return false;
  }
}

// ── API functions ─────────────────────────────────────────────────────────────

/** POST /api/chat/ — send a text message and receive an AI reply. */
export async function sendMessage(
  message: string,
  conversationId: number | null
): Promise<{ data: ChatResponse } | { error: string }> {
  return postJson<ChatResponse>("/api/chat/", {
    message,
    ...(conversationId !== null ? { conversation_id: conversationId } : {}),
  });
}

/** GET /api/chat/<id>/history/ — reload all messages for a conversation. */
export async function fetchHistory(
  conversationId: number
): Promise<{ data: HistoryResponse } | { error: string }> {
  return getJson<HistoryResponse>(`/api/chat/${conversationId}/history/`);
}

/**
 * POST /api/upload/ — upload a media file with real-time progress reporting.
 *
 * Uses XHR (not fetch) because the Fetch API does not expose upload progress.
 * Applies a 120-second timeout on the XHR to prevent UI hangs on large files.
 *
 * Size limits (enforced server-side, shown client-side for UX):
 *   image  ≤ 5 MB  (JPEG, PNG, WebP)
 *   audio  ≤ 10 MB (MP3, WAV, M4A)
 *   video  ≤ 25 MB (MP4, MOV)
 */
export async function uploadMedia(
  file: File,
  mediaType: "image" | "audio" | "video",
  conversationId: number,
  onProgress?: (pct: number) => void
): Promise<{ data: UploadResponse } | { error: string }> {
  // Client-side size guard — gives immediate feedback before the upload even starts
  const maxBytes: Record<string, number> = {
    image: 5 * 1024 * 1024,
    audio: 10 * 1024 * 1024,
    video: 25 * 1024 * 1024,
  };
  if (file.size > maxBytes[mediaType]) {
    const maxMb = maxBytes[mediaType] / (1024 * 1024);
    const actualMb = (file.size / (1024 * 1024)).toFixed(1);
    return {
      error: `File too large (${actualMb} MB). Maximum for ${mediaType} is ${maxMb} MB.`,
    };
  }

  return new Promise((resolve) => {
    const form = new FormData();
    form.append("file", file);
    form.append("media_type", mediaType);
    form.append("conversation_id", String(conversationId));

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/api/upload/`);
    xhr.setRequestHeader("Accept", "application/json");
    xhr.timeout = UPLOAD_TIMEOUT_MS;

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      try {
        const json = JSON.parse(xhr.responseText);
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve({ data: json as UploadResponse });
        } else {
          resolve({ error: extractError(json) });
        }
      } catch {
        resolve({ error: "Invalid response from server during upload." });
      }
    };

    xhr.onerror = () => resolve({ error: "Network error during upload. Check your connection." });
    xhr.ontimeout = () =>
      resolve({
        error: `Upload timed out after ${UPLOAD_TIMEOUT_MS / 1000}s. The file may be too large or the connection too slow.`,
      });

    xhr.send(form);
  });
}

/** POST /api/booking/ — create a service booking. */
export async function createBooking(payload: {
  conversation_id: number;
  customer_name: string;
  customer_contact: string;
  car_model: string;
  issue_summary: string;
  service: string;
}): Promise<{ data: BookingData } | { error: string; fieldErrors?: BookingErrors }> {
  return postJson<BookingData>("/api/booking/", payload);
}
