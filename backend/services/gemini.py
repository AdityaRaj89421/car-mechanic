"""
services/gemini.py — Gemini AI wrapper for the AI Car Mechanic.

Responsibilities:
  - Load GEMINI_API_KEY from environment
  - Enforce the senior automobile technician system prompt
  - Enforce a strict JSON response contract via Gemini's response_schema
  - Send text conversations + optional image bytes to Gemini
  - Parse and validate the response defensively
  - Wrap every network/API call in try/except — never propagate exceptions
    that would 500 a request; always return a structured error dict instead

Response contract (always returned from call_gemini):
  {
    "status":  "need_more_info" | "diagnosis_ready" | "off_topic" | "error",

    # need_more_info
    "question": str,

    # diagnosis_ready
    "diagnosis":       str,
    "symptoms":        str,
    "recommendation":  str,

    # off_topic
    "message": str,

    # error (AI unavailable, bad key, timeout, etc.)
    "error": str,
  }
"""

import base64
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert senior automobile technician with 25+ years of hands-on
experience diagnosing and repairing all types of vehicles. You are helping a
customer diagnose their car problem through a chat interface.

YOUR PERSONA:
- Calm, professional, methodical — like a trusted mechanic at a quality garage
- Use clear plain language; avoid unnecessary jargon
- Be empathetic: car problems cause stress and expense

YOUR RULES — follow these strictly:
1. ONLY discuss car/vehicle-related topics (diagnosis, repair, maintenance, parts,
   safety, driving issues). For anything unrelated, respond with status "off_topic".
2. If you do not have enough information to make a confident diagnosis, respond with
   status "need_more_info" and ask ONE specific, focused follow-up question.
3. Once you have gathered sufficient information (symptoms, context, observations),
   respond with status "diagnosis_ready" and provide a clear, actionable diagnosis.
4. If an image is provided, examine it carefully for visible damage, leaks, wear,
   corrosion, or anything abnormal that helps explain the car problem.
5. Never make up information. If you genuinely cannot diagnose remotely, say so
   honestly and recommend a professional in-person inspection.

YOUR RESPONSE FORMAT — you MUST respond ONLY with valid JSON, no prose outside JSON:

For insufficient information:
{
  "status": "need_more_info",
  "question": "<single focused follow-up question>"
}

For a completed diagnosis:
{
  "status": "diagnosis_ready",
  "diagnosis": "<clear diagnosis — what is wrong and why>",
  "symptoms": "<summary of the symptoms that led to this conclusion>",
  "recommendation": "<specific, actionable next steps the customer should take>"
}

For off-topic queries:
{
  "status": "off_topic",
  "message": "<polite refusal explaining you only handle vehicle-related questions>"
}"""

# ── Response schema (used with Gemini structured output) ─────────────────────

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["need_more_info", "diagnosis_ready", "off_topic"],
        },
        "question": {"type": "string"},
        "diagnosis": {"type": "string"},
        "symptoms": {"type": "string"},
        "recommendation": {"type": "string"},
        "message": {"type": "string"},
    },
    "required": ["status"],
}

# ── Client factory (lazy, cached) ─────────────────────────────────────────────

_client = None


def _get_client():
    """Return a cached google-genai Client, or None if the key is missing."""
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.error("GEMINI_API_KEY is not set — AI features will be unavailable.")
        return None
    try:
        from google import genai  # noqa: PLC0415
        _client = genai.Client(api_key=api_key)
        return _client
    except Exception as exc:
        logger.exception("Failed to initialise Gemini client: %s", exc)
        return None


# ── Core public function ──────────────────────────────────────────────────────

def call_gemini(
    messages: list[dict[str, str]],
    image_bytes: bytes | None = None,
    image_mime: str = "image/jpeg",
) -> dict[str, Any]:
    """
    Send a conversation to Gemini and return a structured response dict.

    Args:
        messages:    List of {"role": "user"|"model", "text": str} dicts
                     in chronological order. The LAST entry is the current
                     user turn.
        image_bytes: Raw bytes of an image to include in the current turn,
                     or None for text-only.
        image_mime:  MIME type of the image (default "image/jpeg").

    Returns:
        A dict matching the response contract described in the module docstring.
        Never raises — on any failure returns {"status": "error", "error": ...}.
    """
    client = _get_client()
    if client is None:
        return {
            "status": "error",
            "error": "ai_unavailable: GEMINI_API_KEY is not configured.",
        }

    try:
        from google.genai import types as genai_types  # noqa: PLC0415

        # ── Build the contents list for the Gemini API ─────────────────────
        # Gemini uses role "user" / "model" (not "assistant")
        contents = []
        for i, msg in enumerate(messages):
            role = "model" if msg["role"] == "assistant" else "user"
            is_last = i == len(messages) - 1

            if is_last and image_bytes:
                # Attach the image to the final user turn
                contents.append(
                    genai_types.Content(
                        role=role,
                        parts=[
                            genai_types.Part(text=msg["text"]),
                            genai_types.Part(
                                inline_data=genai_types.Blob(
                                    mime_type=image_mime,
                                    data=image_bytes,
                                )
                            ),
                        ],
                    )
                )
            else:
                contents.append(
                    genai_types.Content(
                        role=role,
                        parts=[genai_types.Part(text=msg["text"])],
                    )
                )

        # ── Call Gemini with structured output ────────────────────────────
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents,
            config=genai_types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=_RESPONSE_SCHEMA,
                temperature=0.3,        # lower = more deterministic for diagnosis
                max_output_tokens=1024,
            ),
        )

        raw_text = response.text.strip()
        return _parse_response(raw_text)

    except Exception as exc:
        logger.exception("Gemini API call failed: %s", exc)
        return {
            "status": "error",
            "error": f"ai_unavailable: {type(exc).__name__}",
        }


# ── Response parsing & validation ────────────────────────────────────────────

def _parse_response(raw: str) -> dict[str, Any]:
    """
    Parse and defensively validate the raw JSON string from Gemini.

    If parsing fails or required fields are missing, returns an error dict
    rather than raising.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Gemini returned invalid JSON: %s | raw=%r", exc, raw[:300])
        return {
            "status": "error",
            "error": "ai_unavailable: malformed JSON response from AI.",
        }

    if not isinstance(data, dict):
        return {"status": "error", "error": "ai_unavailable: unexpected response shape."}

    status_val = data.get("status")

    if status_val == "need_more_info":
        question = data.get("question", "").strip()
        if not question:
            logger.warning("need_more_info response missing 'question' field: %r", data)
            question = "Could you please provide more details about the issue?"
        return {"status": "need_more_info", "question": question}

    if status_val == "diagnosis_ready":
        return {
            "status": "diagnosis_ready",
            "diagnosis": data.get("diagnosis", "").strip(),
            "symptoms": data.get("symptoms", "").strip(),
            "recommendation": data.get("recommendation", "").strip(),
        }

    if status_val == "off_topic":
        return {
            "status": "off_topic",
            "message": data.get("message", "I can only assist with vehicle-related questions."),
        }

    logger.warning("Unexpected status from Gemini: %r — full response: %r", status_val, data)
    return {
        "status": "error",
        "error": f"ai_unavailable: unexpected status value '{status_val}'.",
    }
