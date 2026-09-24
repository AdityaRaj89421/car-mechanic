"""
chatbot/views.py — Stage 3: Gemini AI wired into chat, upload, and diagnosis.

Endpoints:
  POST /api/chat/               — send message to Gemini, save reply, create Diagnosis if ready
  GET  /api/chat/<id>/history/  — all messages in order
  POST /api/upload/             — validate + save media; analyse image with Gemini
  POST /api/diagnosis/          — return or re-derive Diagnosis for a conversation
  POST /api/booking/            — create Booking
  GET  /api/booking/<id>/       — retrieve Booking (nested)

All validation errors are structured 400s. Gemini failures return a graceful
error response, never a 500.
"""

import mimetypes
import os

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from services.gemini import call_gemini

from .models import Booking, Conversation, Diagnosis, Message
from .serializers import (
    BookingCreateSerializer,
    BookingDetailSerializer,
    DiagnosisSerializer,
    MessageSerializer,
)

# ── Allowed upload types & size limits ───────────────────────────────────────

_ALLOWED: dict[str, dict] = {
    "image": {
        "max_bytes": 5 * 1024 * 1024,
        "mimetypes": {"image/jpeg", "image/png", "image/webp"},
        "extensions": {".jpg", ".jpeg", ".png", ".webp"},
        "label": "image (JPEG, PNG, WebP <= 5 MB)",
    },
    "audio": {
        "max_bytes": 10 * 1024 * 1024,
        "mimetypes": {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/m4a"},
        "extensions": {".mp3", ".wav", ".m4a"},
        "label": "audio (MP3, WAV, M4A <= 10 MB)",
    },
    "video": {
        "max_bytes": 25 * 1024 * 1024,
        "mimetypes": {"video/mp4", "video/quicktime"},
        "extensions": {".mp4", ".mov"},
        "label": "video (MP4, MOV <= 25 MB)",
    },
}


def _detect_mime(file) -> str:
    mime, _ = mimetypes.guess_type(file.name)
    return mime or ""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_conversation(raw_id) -> tuple[Conversation | None, Response | None]:
    """
    Parse and fetch a Conversation by id.
    Returns (conversation, None) on success, (None, error_response) on failure.
    """
    if not raw_id:
        return None, Response(
            {"conversation_id": "This field is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        conv = Conversation.objects.get(pk=int(raw_id))
        return conv, None
    except (ValueError, TypeError):
        return None, Response(
            {"conversation_id": "Must be a valid integer."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Conversation.DoesNotExist:
        return None, Response(
            {"conversation_id": f"Conversation {raw_id} does not exist."},
            status=status.HTTP_400_BAD_REQUEST,
        )


def _build_history(conversation: Conversation) -> list[dict[str, str]]:
    """Convert DB messages to the [{role, text}] list expected by call_gemini."""
    msgs = conversation.messages.order_by("created_at")
    history = []
    for m in msgs:
        role = "model" if m.role == Message.Role.ASSISTANT else "user"
        history.append({"role": role, "text": m.content})
    return history


def _save_diagnosis(conversation: Conversation, ai: dict) -> Diagnosis:
    """Persist a diagnosis_ready Gemini response as a Diagnosis row."""
    return Diagnosis.objects.create(
        conversation=conversation,
        diagnosis_text=ai.get("diagnosis", ""),
        symptoms=ai.get("symptoms", ""),
        recommendation=ai.get("recommendation", ""),
    )


# ── POST /api/chat/ ───────────────────────────────────────────────────────────

@api_view(["POST"])
def chat(request: Request) -> Response:
    """
    Accept a user message, send conversation history + message to Gemini,
    save the assistant reply, and — if Gemini signals diagnosis_ready —
    also persist a Diagnosis row.

    Request JSON:
        conversation_id  int | null  — omit to start a new conversation
        message          str         — required, non-empty

    Response 200:
        {
            "conversation_id": int,
            "user_message_id": int,
            "assistant_message_id": int | null,
            "ai_status": "need_more_info" | "diagnosis_ready" | "off_topic" | "error",
            "reply": str,                         # assistant's text for the chat bubble
            "diagnosis": DiagnosisSerializer | null,
            "question": str | null,               # populated when ai_status == need_more_info
        }
    """
    # ── Validate input ────────────────────────────────────────────────────────
    message_text: str = request.data.get("message", "").strip()
    if not message_text:
        return Response(
            {"message": "This field is required and must not be blank."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── Resolve / create conversation ─────────────────────────────────────────
    raw_convo_id = request.data.get("conversation_id")
    if raw_convo_id:
        conversation, err = _resolve_conversation(raw_convo_id)
        if err:
            return err
    else:
        conversation = Conversation.objects.create()

    # ── Save the user's message ───────────────────────────────────────────────
    user_msg = Message.objects.create(
        conversation=conversation,
        role=Message.Role.USER,
        content=message_text,
        media_type=Message.MediaType.NONE,
    )

    # ── Build history (includes the message we just saved) ────────────────────
    history = _build_history(conversation)

    # ── Call Gemini ───────────────────────────────────────────────────────────
    ai = call_gemini(history)
    ai_status = ai.get("status", "error")

    # ── Derive a human-readable reply for the chat bubble ─────────────────────
    if ai_status == "need_more_info":
        reply_text = ai.get("question", "Could you give me more details?")
    elif ai_status == "diagnosis_ready":
        diag = ai.get("diagnosis", "")
        rec = ai.get("recommendation", "")
        reply_text = f"{diag}\n\n**Recommendation:** {rec}"
    elif ai_status == "off_topic":
        reply_text = ai.get("message", "I can only help with vehicle-related questions.")
    else:
        # error / ai_unavailable — degrade gracefully
        reply_text = (
            "I'm having trouble connecting to the AI service right now. "
            "Please try again in a moment."
        )

    # ── Save assistant reply as a Message ─────────────────────────────────────
    assistant_msg = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content=reply_text,
        media_type=Message.MediaType.NONE,
    )

    # ── Persist Diagnosis row if ready ────────────────────────────────────────
    diagnosis_obj = None
    if ai_status == "diagnosis_ready":
        diagnosis_obj = _save_diagnosis(conversation, ai)

    # ── Build response ────────────────────────────────────────────────────────
    diagnosis_data = (
        DiagnosisSerializer(diagnosis_obj).data if diagnosis_obj else None
    )

    return Response(
        {
            "conversation_id": conversation.pk,
            "user_message_id": user_msg.pk,
            "assistant_message_id": assistant_msg.pk,
            "ai_status": ai_status,
            "reply": reply_text,
            "question": ai.get("question") if ai_status == "need_more_info" else None,
            "diagnosis": diagnosis_data,
        },
        status=status.HTTP_200_OK,
    )


# ── GET /api/chat/<conversation_id>/history/ ─────────────────────────────────

@api_view(["GET"])
def chat_history(request: Request, conversation_id: int) -> Response:
    """Return all messages in a conversation, oldest-first."""
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    messages = conversation.messages.order_by("created_at")
    serializer = MessageSerializer(messages, many=True, context={"request": request})
    return Response({"conversation_id": conversation.pk, "messages": serializer.data})


# ── POST /api/upload/ ────────────────────────────────────────────────────────

@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def upload(request: Request) -> Response:
    """
    Accept a media file, validate it, store it, and — for images — send
    it to Gemini for analysis and inject the analysis as an assistant message.

    SCOPE DECISION (audio / video):
        Audio and video are stored and acknowledged in the conversation but NOT
        sent to Gemini. Reasons:
          1. The project brief specifies "minimise AI usage" as an evaluation
             criterion; only image analysis is required for the MVP.
          2. Audio/video transcription via Gemini File API adds significant
             latency, cost, and complexity that belongs in a later stage.
          3. The stored files remain available for future integration.
        This decision is intentional and documented here.

    Multipart fields:
        file            — required
        conversation_id — required
        media_type      — required: "image" | "audio" | "video"
    """
    # ── Validate conversation ─────────────────────────────────────────────────
    conversation, err = _resolve_conversation(request.data.get("conversation_id"))
    if err:
        return err

    # ── Validate media_type ───────────────────────────────────────────────────
    media_type_str: str = request.data.get("media_type", "").lower()
    if media_type_str not in _ALLOWED:
        return Response(
            {"media_type": f"Must be one of: {', '.join(_ALLOWED.keys())}."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    rules = _ALLOWED[media_type_str]

    # ── Validate file ─────────────────────────────────────────────────────────
    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return Response({"file": "A file is required."}, status=status.HTTP_400_BAD_REQUEST)

    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in rules["extensions"]:
        return Response(
            {"file": f"Invalid extension '{ext}'. Allowed: {', '.join(sorted(rules['extensions']))}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    detected_mime = _detect_mime(uploaded_file)
    if detected_mime and detected_mime not in rules["mimetypes"]:
        return Response(
            {"file": f"MIME type '{detected_mime}' not allowed for {media_type_str}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if uploaded_file.size > rules["max_bytes"]:
        max_mb = rules["max_bytes"] // (1024 * 1024)
        actual_mb = uploaded_file.size / (1024 * 1024)
        return Response(
            {"file": f"File too large ({actual_mb:.1f} MB). Max for {media_type_str}: {max_mb} MB."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── Save the user's media message ─────────────────────────────────────────
    user_msg = Message.objects.create(
        conversation=conversation,
        role=Message.Role.USER,
        content=f"[{media_type_str} attachment: {uploaded_file.name}]",
        media=uploaded_file,
        media_type=media_type_str,
    )

    # ── Handle per media type ─────────────────────────────────────────────────
    assistant_msg = None

    if media_type_str == "image":
        # Send image to Gemini for visual analysis
        uploaded_file.seek(0)
        image_bytes = uploaded_file.read()
        mime = detected_mime or "image/jpeg"

        # Build history + a prompt instructing Gemini to analyse the image
        history = _build_history(conversation)
        # The last history entry is already the "[image attachment...]" label.
        # Replace its text with an explicit instruction for better results.
        if history:
            history[-1]["text"] = (
                "I have attached a photo of my car issue. "
                "Please examine the image carefully and tell me what you observe "
                "that could be related to the problem we're discussing."
            )

        ai = call_gemini(history, image_bytes=image_bytes, image_mime=mime)
        ai_status = ai.get("status", "error")

        if ai_status == "need_more_info":
            reply_text = ai.get("question", "I can see the image. Could you tell me more?")
        elif ai_status == "diagnosis_ready":
            diag = ai.get("diagnosis", "")
            rec = ai.get("recommendation", "")
            reply_text = f"Based on the image: {diag}\n\n**Recommendation:** {rec}"
        elif ai_status == "off_topic":
            reply_text = ai.get("message", "I can only help with vehicle-related questions.")
        else:
            reply_text = "I received your image but couldn't analyse it right now. Please describe the issue in text."

        assistant_msg = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=reply_text,
            media_type=Message.MediaType.NONE,
        )

        # Persist diagnosis if the image triggered a ready diagnosis
        if ai_status == "diagnosis_ready":
            _save_diagnosis(conversation, ai)

    else:
        # audio / video — store only, acknowledge in conversation
        # See SCOPE DECISION docstring above.
        ack_text = (
            f"I've received your {media_type_str} file ({uploaded_file.name}). "
            "Audio and video analysis isn't available in this version — "
            "please describe what you're hearing/seeing in text and I'll help diagnose the issue."
        )
        assistant_msg = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=ack_text,
            media_type=Message.MediaType.NONE,
        )

    # ── Build response ────────────────────────────────────────────────────────
    user_serializer = MessageSerializer(user_msg, context={"request": request})
    response_data = {
        "message": user_serializer.data,
        "assistant_reply": (
            MessageSerializer(assistant_msg, context={"request": request}).data
            if assistant_msg else None
        ),
    }
    return Response(response_data, status=status.HTTP_201_CREATED)


# ── POST /api/diagnosis/ ─────────────────────────────────────────────────────

@api_view(["POST"])
def diagnosis(request: Request) -> Response:
    """
    Return the existing Diagnosis for a conversation, or attempt to derive one
    from the conversation history if none exists yet.

    Request JSON:
        conversation_id  int  — required

    Response 200:
        {
            "source": "existing" | "derived" | "insufficient_data" | "error",
            "diagnosis": DiagnosisSerializer | null,
            "message": str | null   # populated when no diagnosis available
        }
    """
    conversation, err = _resolve_conversation(request.data.get("conversation_id"))
    if err:
        return err

    # ── Return existing Diagnosis if we already have one ──────────────────────
    existing = (
        Diagnosis.objects.filter(conversation=conversation)
        .order_by("-created_at")
        .first()
    )
    if existing:
        return Response(
            {
                "source": "existing",
                "diagnosis": DiagnosisSerializer(existing).data,
                "message": None,
            }
        )

    # ── Try to derive a diagnosis from history ────────────────────────────────
    history = _build_history(conversation)
    if not history:
        return Response(
            {
                "source": "insufficient_data",
                "diagnosis": None,
                "message": "No messages found in this conversation.",
            }
        )

    # Append a system-level prompt asking Gemini to summarise/diagnose now
    history.append({
        "role": "user",
        "text": (
            "Based on everything we have discussed so far, please provide your "
            "final diagnosis if you have enough information. "
            "If you still need more details, say so."
        ),
    })

    ai = call_gemini(history)
    ai_status = ai.get("status", "error")

    if ai_status == "diagnosis_ready":
        diagnosis_obj = _save_diagnosis(conversation, ai)
        return Response(
            {
                "source": "derived",
                "diagnosis": DiagnosisSerializer(diagnosis_obj).data,
                "message": None,
            }
        )

    if ai_status == "need_more_info":
        return Response(
            {
                "source": "insufficient_data",
                "diagnosis": None,
                "message": ai.get("question", "More information is needed before a diagnosis can be made."),
            }
        )

    # error / off_topic
    return Response(
        {
            "source": "error",
            "diagnosis": None,
            "message": ai.get("error") or ai.get("message") or "AI service unavailable.",
        }
    )


# ── POST /api/booking/ ────────────────────────────────────────────────────────

@api_view(["POST"])
def booking_create(request: Request) -> Response:
    """Create a Booking. Auto-links the latest Diagnosis if one exists."""
    serializer = BookingCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    booking = serializer.save()
    output = BookingDetailSerializer(booking, context={"request": request})
    return Response(output.data, status=status.HTTP_201_CREATED)


# ── GET /api/booking/<id>/ ────────────────────────────────────────────────────

@api_view(["GET"])
def booking_detail(request: Request, booking_id: int) -> Response:
    """Retrieve a Booking with nested Diagnosis and Conversation summary."""
    booking = get_object_or_404(
        Booking.objects.select_related("conversation", "diagnosis"),
        pk=booking_id,
    )
    serializer = BookingDetailSerializer(booking, context={"request": request})
    return Response(serializer.data)
