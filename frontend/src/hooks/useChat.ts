"use client";

/**
 * useChat — central state machine for the chat interface.
 *
 * Manages: conversation_id, messages, diagnosis, loading/uploading flags,
 * upload progress, errors, and the booking modal.
 *
 * Persists conversation_id to sessionStorage so a page refresh reloads history.
 */

import { useCallback, useEffect, useReducer, useRef } from "react";
import { fetchHistory, sendMessage, uploadMedia } from "@/services/api";
import type { DiagnosisData, MessageData } from "@/types/chat";

// ── State ─────────────────────────────────────────────────────────────────────

export interface ChatState {
  conversationId: number | null;
  messages: MessageData[];
  diagnosis: DiagnosisData | null;
  isLoading: boolean;
  uploadProgress: number | null; // null = idle, 0-100 = uploading
  error: string | null;
  bookingModalOpen: boolean;
}

const initial: ChatState = {
  conversationId: null,
  messages: [],
  diagnosis: null,
  isLoading: false,
  uploadProgress: null,
  error: null,
  bookingModalOpen: false,
};

// ── Actions ───────────────────────────────────────────────────────────────────

type Action =
  | { type: "SET_CONVERSATION"; id: number }
  | { type: "SET_MESSAGES"; messages: MessageData[] }
  | { type: "APPEND_MESSAGE"; message: MessageData }
  | { type: "APPEND_MESSAGES"; messages: MessageData[] }
  | { type: "SET_DIAGNOSIS"; diagnosis: DiagnosisData }
  | { type: "SET_LOADING"; loading: boolean }
  | { type: "SET_UPLOAD_PROGRESS"; progress: number | null }
  | { type: "SET_ERROR"; error: string | null }
  | { type: "SET_BOOKING_MODAL"; open: boolean }
  | { type: "RESET" };

function reducer(state: ChatState, action: Action): ChatState {
  switch (action.type) {
    case "SET_CONVERSATION":
      return { ...state, conversationId: action.id };
    case "SET_MESSAGES":
      return { ...state, messages: action.messages };
    case "APPEND_MESSAGE":
      return { ...state, messages: [...state.messages, action.message] };
    case "APPEND_MESSAGES":
      return { ...state, messages: [...state.messages, ...action.messages] };
    case "SET_DIAGNOSIS":
      return { ...state, diagnosis: action.diagnosis };
    case "SET_LOADING":
      return { ...state, isLoading: action.loading, error: action.loading ? null : state.error };
    case "SET_UPLOAD_PROGRESS":
      return { ...state, uploadProgress: action.progress };
    case "SET_ERROR":
      return { ...state, error: action.error, isLoading: false };
    case "SET_BOOKING_MODAL":
      return { ...state, bookingModalOpen: action.open };
    case "RESET":
      sessionStorage.removeItem("car_mechanic_convo_id");
      return initial;
    default:
      return state;
  }
}

// ── Storage key ───────────────────────────────────────────────────────────────

const STORAGE_KEY = "car_mechanic_convo_id";

// ── Hook ──────────────────────────────────────────────────────────────────────

/** Synthetic message created client-side to show user text immediately. */
function optimisticUserMessage(
  conversationId: number,
  content: string,
  mediaType: "none" | "image" | "audio" | "video" = "none"
): MessageData {
  return {
    id: Date.now(), // temporary, replaced once server confirms
    conversation_id: conversationId,
    role: "user",
    content,
    media_url: null,
    media_type: mediaType,
    created_at: new Date().toISOString(),
  };
}

/** Synthetic assistant "thinking" placeholder. */
function thinkingMessage(conversationId: number): MessageData {
  return {
    id: -1,
    conversation_id: conversationId,
    role: "assistant",
    content: "__thinking__",
    media_url: null,
    media_type: "none",
    created_at: new Date().toISOString(),
  };
}

export function useChat() {
  const [state, dispatch] = useReducer(reducer, initial);
  const bottomRef = useRef<HTMLDivElement>(null);

  // ── Restore from sessionStorage on mount ──────────────────────────────────
  useEffect(() => {
    const stored = sessionStorage.getItem(STORAGE_KEY);
    if (!stored) return;
    const id = parseInt(stored, 10);
    if (isNaN(id)) return;

    dispatch({ type: "SET_CONVERSATION", id });
    fetchHistory(id).then((result) => {
      if ("data" in result) {
        dispatch({ type: "SET_MESSAGES", messages: result.data.messages });
      }
    });
  }, []);

  // ── Auto-scroll on new messages ────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [state.messages, state.isLoading]);

  // ── Send text message ──────────────────────────────────────────────────────
  const sendText = useCallback(
    async (text: string) => {
      if (!text.trim() || state.isLoading) return;

      const tempConvoId = state.conversationId ?? 0;

      // Show user message immediately (optimistic)
      dispatch({ type: "APPEND_MESSAGE", message: optimisticUserMessage(tempConvoId, text) });
      dispatch({ type: "SET_LOADING", loading: true });

      // Show thinking indicator
      dispatch({ type: "APPEND_MESSAGE", message: thinkingMessage(tempConvoId) });

      const result = await sendMessage(text, state.conversationId);

      if ("error" in result) {
        dispatch({ type: "SET_ERROR", error: result.error });
        // Remove the thinking placeholder (id=-1) from message list
        dispatch({ type: "SET_LOADING", loading: false });
        return;
      }

      const { data } = result;

      // Persist conversation id
      if (!state.conversationId) {
        dispatch({ type: "SET_CONVERSATION", id: data.conversation_id });
        sessionStorage.setItem(STORAGE_KEY, String(data.conversation_id));
      }

      // Reload authoritative history (replaces optimistic messages + thinking)
      const history = await fetchHistory(data.conversation_id);
      if ("data" in history) {
        dispatch({ type: "SET_MESSAGES", messages: history.data.messages });
      }

      // Surface diagnosis if returned
      if (data.diagnosis) {
        dispatch({ type: "SET_DIAGNOSIS", diagnosis: data.diagnosis });
      }

      dispatch({ type: "SET_LOADING", loading: false });
    },
    [state.conversationId, state.isLoading]
  );

  // ── Upload media file ──────────────────────────────────────────────────────
  const upload = useCallback(
    async (file: File, mediaType: "image" | "audio" | "video") => {
      if (state.uploadProgress !== null) return; // already uploading

      // Ensure we have a conversation — create one via a dummy message if needed
      let convoId = state.conversationId;
      if (!convoId) {
        dispatch({ type: "SET_ERROR", error: "Please send a text message first to start a conversation." });
        return;
      }

      dispatch({ type: "SET_UPLOAD_PROGRESS", progress: 0 });

      const result = await uploadMedia(file, mediaType, convoId, (pct) => {
        dispatch({ type: "SET_UPLOAD_PROGRESS", progress: pct });
      });

      dispatch({ type: "SET_UPLOAD_PROGRESS", progress: null });

      if ("error" in result) {
        dispatch({ type: "SET_ERROR", error: result.error });
        return;
      }

      // Reload history to show the uploaded message + assistant reply
      const history = await fetchHistory(convoId);
      if ("data" in history) {
        dispatch({ type: "SET_MESSAGES", messages: history.data.messages });
      }
    },
    [state.conversationId, state.uploadProgress]
  );

  return {
    state,
    bottomRef,
    sendText,
    upload,
    openBooking: () => dispatch({ type: "SET_BOOKING_MODAL", open: true }),
    closeBooking: () => dispatch({ type: "SET_BOOKING_MODAL", open: false }),
    clearError: () => dispatch({ type: "SET_ERROR", error: null }),
    reset: () => dispatch({ type: "RESET" }),
  };
}
