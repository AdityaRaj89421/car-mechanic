"""
chatbot/serializers.py — DRF serializers for all four models.

Provides:
- Field-level validation errors (400, never 500)
- Nested read representations for Booking detail
- Media URL resolution for Message
"""

from rest_framework import serializers
from django.conf import settings

from .models import Booking, Conversation, Diagnosis, Message


# ── Conversation ──────────────────────────────────────────────────────────────

class ConversationSerializer(serializers.ModelSerializer):
    """Minimal representation of a Conversation (used as nested context)."""

    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ["id", "created_at", "message_count"]
        read_only_fields = fields

    def get_message_count(self, obj: Conversation) -> int:
        return obj.messages.count()


# ── Message ───────────────────────────────────────────────────────────────────

class MessageSerializer(serializers.ModelSerializer):
    """
    Full representation of a Message, including an absolute media_url
    so the client never has to construct storage paths itself.
    """

    media_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation_id",
            "role",
            "content",
            "media_url",
            "media_type",
            "created_at",
        ]
        read_only_fields = fields

    def get_media_url(self, obj: Message) -> str | None:
        """Return an absolute URL for the media file, or None."""
        if not obj.media:
            return None
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(obj.media.url)
        # Fallback when no request context is available
        return f"{settings.MEDIA_URL}{obj.media.name}"


# ── Diagnosis ─────────────────────────────────────────────────────────────────

class DiagnosisSerializer(serializers.ModelSerializer):
    """Full representation of a Diagnosis."""

    class Meta:
        model = Diagnosis
        fields = [
            "id",
            "conversation_id",
            "diagnosis_text",
            "symptoms",
            "recommendation",
            "created_at",
        ]
        read_only_fields = fields


# ── Booking ───────────────────────────────────────────────────────────────────

class BookingCreateSerializer(serializers.Serializer):
    """
    Write-only serializer for POST /api/booking/.

    Uses a plain Serializer (not ModelSerializer) so we can express
    cross-field validation (diagnosis auto-linking) cleanly.
    """

    conversation_id = serializers.IntegerField()
    customer_name = serializers.CharField(max_length=255)
    customer_contact = serializers.CharField(max_length=255)
    car_model = serializers.CharField(max_length=255)
    issue_summary = serializers.CharField()
    service = serializers.CharField(max_length=255)

    def validate_conversation_id(self, value: int) -> int:
        """Ensure the referenced conversation exists."""
        if not Conversation.objects.filter(pk=value).exists():
            raise serializers.ValidationError(
                f"Conversation with id={value} does not exist."
            )
        return value

    def validate_customer_contact(self, value: str) -> str:
        """Ensure contact is non-empty after stripping whitespace."""
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Customer contact must not be blank.")
        return stripped

    def create(self, validated_data: dict) -> Booking:
        """
        Create the Booking and auto-link the most recent Diagnosis for
        that Conversation if one exists.
        """
        conversation = Conversation.objects.get(pk=validated_data.pop("conversation_id"))
        # Auto-link the latest diagnosis for this conversation (may be None)
        latest_diagnosis = (
            Diagnosis.objects.filter(conversation=conversation)
            .order_by("-created_at")
            .first()
        )
        return Booking.objects.create(
            conversation=conversation,
            diagnosis=latest_diagnosis,
            **validated_data,
        )


class BookingDetailSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for GET /api/booking/<id>/.
    Nests the related Diagnosis and a Conversation summary.
    """

    diagnosis = DiagnosisSerializer(read_only=True)
    conversation = ConversationSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "conversation",
            "customer_name",
            "customer_contact",
            "car_model",
            "issue_summary",
            "diagnosis",
            "service",
            "status",
            "created_at",
        ]
        read_only_fields = fields
