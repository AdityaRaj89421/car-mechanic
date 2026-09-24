/**
 * Shared TypeScript types for the AI Car Mechanic chat system.
 * Mirrors the Django model/serializer shapes from the backend.
 */

export type MessageRole = "user" | "assistant";
export type MediaType = "image" | "audio" | "video" | "none";
export type AiStatus = "need_more_info" | "diagnosis_ready" | "off_topic" | "error";
export type BookingStatus = "pending" | "confirmed" | "completed";

/** A single chat message as returned by the API. */
export interface MessageData {
  id: number;
  conversation_id: number;
  role: MessageRole;
  content: string;
  media_url: string | null;
  media_type: MediaType;
  created_at: string;
}

/** A diagnosis produced by Gemini. */
export interface DiagnosisData {
  id: number;
  conversation_id: number;
  diagnosis_text: string;
  symptoms: string;
  recommendation: string;
  created_at: string;
}

/** Nested booking response from /api/booking/<id>/. */
export interface BookingData {
  id: number;
  customer_name: string;
  customer_contact: string;
  car_model: string;
  issue_summary: string;
  service: string;
  status: BookingStatus;
  diagnosis: DiagnosisData | null;
  conversation: { id: number; created_at: string; message_count: number };
  created_at: string;
}

/** Response from POST /api/chat/. */
export interface ChatResponse {
  conversation_id: number;
  user_message_id: number;
  assistant_message_id: number;
  ai_status: AiStatus;
  reply: string;
  question: string | null;
  diagnosis: DiagnosisData | null;
}

/** Response from GET /api/chat/<id>/history/. */
export interface HistoryResponse {
  conversation_id: number;
  messages: MessageData[];
}

/** Response from POST /api/upload/. */
export interface UploadResponse {
  message: MessageData;
  assistant_reply: MessageData | null;
}

/** Booking field-level errors returned on 400. */
export type BookingErrors = Partial<Record<
  "conversation_id" | "customer_name" | "customer_contact" | "car_model" | "issue_summary" | "service",
  string | string[]
>>;
