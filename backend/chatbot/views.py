"""
chatbot/views.py — Real API view implementations for Stage 2.

Endpoints implemented:
  POST /api/chat/           — save user message, create conversation if needed
  GET  /api/chat/<id>/history/ — return all messages for a conversation
  POST /api/upload/         — validate + save media file, create Message
  POST /api/diagnosis/      — STUB (Stage 3 will call Gemini)
  POST /api/booking/        — create Booking with validation
  GET  /api/booking/<id>/   — retrieve Booking with nested Diagnosis + Conversation

All validation errors return structured 400 responses with field-level detail.
No 500s should be reachable through expected client input.
"""

import os
import mimetypes

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Booking, Conversation, Diagnosis, Message
from .serializers import (
    BookingCreateSerializer,
    BookingDetailSerializer,
    DiagnosisSerializer,
    MessageSerializer,
)


# ── Allowed file types & sizes ────────────────────────────────────────────────

_ALLOWED: dict[str, dict] = {
    "image": {
        "max_bytes": 5 * 1024 * 1024,          # 5 MB
        "mimetypes": {"image/jpeg", "image/png", "image/webp"},
        "extensions": {".jpg", ".jpeg", ".png", ".webp"},
        "label": "image (JPEG, PNG, WebP ≤ 5 MB)",
    },
    "audio": {
        "max_bytes": 10 * 1024 * 1024,         # 10 MB
        "mimetypes": {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/m4a"},
        "extensions": {".mp3", ".wav", ".m4a"},
        "label": "audio (MP3, WAV, M4A ≤ 10 MB)",
    },
    "video": {
        "max_bytes": 25 * 1024 * 1024,         # 25 MB
        "mimetypes": {"video/mp4", "video/quicktime"},
        "extensions": {".mp4", ".mov"},
        "label": "video (MP4, MOV ≤ 25 MB)",
    },
}


def _detect_mime(file) -> str:
    """Return the MIME type inferred from the file name, or empty string."""
    mime, _ = mimetypes.guess_type(file.name)
    return mime or ""


# ── POST /api/chat/ ───────────────────────────────────────────────────────────

@api_view(["POST"])
def chat(request: Request) -> Response:
    """
    Accept a user text message and persist it.

    Request body (JSON):
        conversation_id  int | null  — omit or null to start a new conversation
        message          str         — required, non-empty

    Response 200:
        {
            "conversation_id": int,
            "message_id": int,
            "message_saved": true
        }
    """
    message_text: str = request.data.get("message", "").strip()
    if not message_text:
        return Response(
            {"message": "This field is required and must not be blank."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    conversation_id = request.data.get("conversation_id")

    # Resolve or create the Conversation
    if conversation_id:
        try:
            conversation_id = int(conversation_id)
            conversation = Conversation.objects.get(pk=conversation_id)
        except (ValueError, TypeError):
            return Response(
                {"conversation_id": "Must be a valid integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Conversation.DoesNotExist:
            return Response(
                {"conversation_id": f"Conversation {conversation_id} does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    else:
        conversation = Conversation.objects.create()

    # Save the user's message
    msg = Message.objects.create(
        conversation=conversation,
        role=Message.Role.USER,
        content=message_text,
        media_type=Message.MediaType.NONE,
    )

    return Response(
        {
            "conversation_id": conversation.pk,
            "message_id": msg.pk,
            "message_saved": True,
        },
        status=status.HTTP_200_OK,
    )


# ── GET /api/chat/<conversation_id>/history/ ─────────────────────────────────

@api_view(["GET"])
def chat_history(request: Request, conversation_id: int) -> Response:
    """
    Return all messages in a conversation, ordered oldest-first.

    Response 200:
        {
            "conversation_id": int,
            "messages": [ MessageSerializer, ... ]
        }
    """
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    messages = conversation.messages.order_by("created_at")
    serializer = MessageSerializer(messages, many=True, context={"request": request})
    return Response(
        {
            "conversation_id": conversation.pk,
            "messages": serializer.data,
        }
    )


# ── POST /api/upload/ ─────────────────────────────────────────────────────────

@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def upload(request: Request) -> Response:
    """
    Accept a media file upload and attach it to a conversation.

    Multipart form fields:
        file            — required
        conversation_id — required (int)
        media_type      — required: "image" | "audio" | "video"

    Validates:
        - media_type is one of the allowed values
        - file extension and MIME type match the declared media_type
        - file does not exceed the size limit for its type

    Response 201: MessageSerializer (with media_url)
    Response 400: { field: error_message }
    """
    # ── Validate conversation_id ──────────────────────────────────────────────
    conversation_id = request.data.get("conversation_id")
    if not conversation_id:
        return Response(
            {"conversation_id": "This field is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        conversation = Conversation.objects.get(pk=int(conversation_id))
    except (ValueError, TypeError):
        return Response(
            {"conversation_id": "Must be a valid integer."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Conversation.DoesNotExist:
        return Response(
            {"conversation_id": f"Conversation {conversation_id} does not exist."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── Validate media_type ───────────────────────────────────────────────────
    media_type_str: str = request.data.get("media_type", "").lower()
    if media_type_str not in _ALLOWED:
        return Response(
            {"media_type": f"Must be one of: {', '.join(_ALLOWED.keys())}."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    rules = _ALLOWED[media_type_str]

    # ── Validate file presence ────────────────────────────────────────────────
    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return Response(
            {"file": "A file is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── Validate file extension ───────────────────────────────────────────────
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in rules["extensions"]:
        allowed = ", ".join(sorted(rules["extensions"]))
        return Response(
            {
                "file": (
                    f"Invalid file type '{ext}' for {media_type_str}. "
                    f"Allowed extensions: {allowed}."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── Validate MIME type ────────────────────────────────────────────────────
    detected_mime = _detect_mime(uploaded_file)
    if detected_mime and detected_mime not in rules["mimetypes"]:
        return Response(
            {
                "file": (
                    f"Detected MIME type '{detected_mime}' is not allowed for "
                    f"{media_type_str}. Expected: {', '.join(sorted(rules['mimetypes']))}."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── Validate file size ────────────────────────────────────────────────────
    if uploaded_file.size > rules["max_bytes"]:
        max_mb = rules["max_bytes"] // (1024 * 1024)
        actual_mb = uploaded_file.size / (1024 * 1024)
        return Response(
            {
                "file": (
                    f"File too large ({actual_mb:.1f} MB). "
                    f"Maximum allowed for {media_type_str} is {max_mb} MB."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── Save message with media ───────────────────────────────────────────────
    msg = Message.objects.create(
        conversation=conversation,
        role=Message.Role.USER,
        content=f"[{media_type_str} attachment: {uploaded_file.name}]",
        media=uploaded_file,
        media_type=media_type_str,
    )

    serializer = MessageSerializer(msg, context={"request": request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# ── POST /api/diagnosis/ — STUB ───────────────────────────────────────────────

@api_view(["POST"])
def diagnosis(request: Request) -> Response:
    """
    POST /api/diagnosis/ — Stage 3 will call Gemini here.

    For now: validate conversation_id exists, then return a placeholder
    Diagnosis object (not persisted).
    """
    conversation_id = request.data.get("conversation_id")
    if not conversation_id:
        return Response(
            {"conversation_id": "This field is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        conversation = Conversation.objects.get(pk=int(conversation_id))
    except (ValueError, TypeError):
        return Response(
            {"conversation_id": "Must be a valid integer."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Conversation.DoesNotExist:
        return Response(
            {"conversation_id": f"Conversation {conversation_id} does not exist."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Return a placeholder — Stage 3 will replace with real Gemini output
    return Response(
        {
            "status": "stub",
            "conversation_id": conversation.pk,
            "diagnosis_text": "[Placeholder] Gemini diagnosis will appear here in Stage 3.",
            "symptoms": "[Placeholder] Symptom analysis pending Gemini integration.",
            "recommendation": "[Placeholder] Service recommendation pending.",
        },
        status=status.HTTP_200_OK,
    )


# ── POST /api/booking/ ────────────────────────────────────────────────────────

@api_view(["POST"])
def booking_create(request: Request) -> Response:
    """
    Create a new Booking linked to a Conversation.

    Request body (JSON):
        conversation_id   int  — required
        customer_name     str  — required
        customer_contact  str  — required
        car_model         str  — required
        issue_summary     str  — required
        service           str  — required

    Auto-links the most recent Diagnosis for the Conversation if one exists.

    Response 201: BookingDetailSerializer
    Response 400: { field: error_message }
    """
    serializer = BookingCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    booking = serializer.save()
    output = BookingDetailSerializer(booking, context={"request": request})
    return Response(output.data, status=status.HTTP_201_CREATED)


# ── GET /api/booking/<id>/ ────────────────────────────────────────────────────

@api_view(["GET"])
def booking_detail(request: Request, booking_id: int) -> Response:
    """
    Retrieve a Booking by ID with nested Diagnosis and Conversation summary.

    Response 200: BookingDetailSerializer
    Response 404: { detail: "Not found." }
    """
    booking = get_object_or_404(
        Booking.objects.select_related("conversation", "diagnosis"),
        pk=booking_id,
    )
    serializer = BookingDetailSerializer(booking, context={"request": request})
    return Response(serializer.data)
