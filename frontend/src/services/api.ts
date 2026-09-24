/**
 * services/api.ts — All HTTP calls to the Django backend.
 *
 * Never throws — always returns { data } | { error }.
 * Callers check the error field and handle it explicitly.
 */

import type {
  BookingData,
  BookingErrors,
  ChatResponse,
  HistoryResponse,
  UploadResponse,
} from "@/types/chat";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// ── Generic fetch helpers ────────────────────────────────────────────────────

async function postJson<T>(
  path: string,
  body: Record<string, unknown>
): Promise<{ data: T } | { error: string; fieldErrors?: BookingErrors }> {
  try {
    const res = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
    });
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
    const res = await fetch(`${BASE}${path}`, {
      headers: { Accept: "application/json" },
    });
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
    // Collect field-level messages
    const msgs = Object.values(obj)
      .flat()
      .filter((v): v is string => typeof v === "string");
    if (msgs.length) return msgs[0];
  }
  return "An unexpected error occurred.";
}

function networkError(err: unknown): string {
  if (err instanceof Error) return `Network error: ${err.message}`;
  return "Network error: could not reach the server.";
}

// ── API functions ────────────────────────────────────────────────────────────

/** POST /api/chat/ — send a text message. */
export async function sendMessage(
  message: string,
  conversationId: number | null
): Promise<{ data: ChatResponse } | { error: string }> {
  return postJson<ChatResponse>("/api/chat/", {
    message,
    ...(conversationId !== null ? { conversation_id: conversationId } : {}),
  });
}

/** GET /api/chat/<id>/history/ — reload a previous conversation. */
export async function fetchHistory(
  conversationId: number
): Promise<{ data: HistoryResponse } | { error: string }> {
  return getJson<HistoryResponse>(`/api/chat/${conversationId}/history/`);
}

/** POST /api/upload/ — upload a media file. */
export async function uploadMedia(
  file: File,
  mediaType: "image" | "audio" | "video",
  conversationId: number,
  onProgress?: (pct: number) => void
): Promise<{ data: UploadResponse } | { error: string }> {
  return new Promise((resolve) => {
    const form = new FormData();
    form.append("file", file);
    form.append("media_type", mediaType);
    form.append("conversation_id", String(conversationId));

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE}/api/upload/`);
    xhr.setRequestHeader("Accept", "application/json");

    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
      };
    }

    xhr.onload = () => {
      try {
        const json = JSON.parse(xhr.responseText);
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve({ data: json as UploadResponse });
        } else {
          resolve({ error: extractError(json) });
        }
      } catch {
        resolve({ error: "Invalid response from server." });
      }
    };

    xhr.onerror = () => resolve({ error: "Network error during upload." });
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
}): Promise<
  { data: BookingData } | { error: string; fieldErrors?: BookingErrors }
> {
  return postJson<BookingData>("/api/booking/", payload);
}
