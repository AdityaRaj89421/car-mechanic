"""
chatbot/models.py — Database schema for the AI Car Mechanic chatbot.

No business logic here — schema only.
"""

from django.db import models


class Conversation(models.Model):
    """Represents a single chat session between a user and the AI mechanic."""

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Conversation #{self.pk} ({self.created_at:%Y-%m-%d %H:%M})"


class Message(models.Model):
    """A single message within a Conversation."""

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        AUDIO = "audio", "Audio"
        VIDEO = "video", "Video"
        NONE = "none", "None"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    media = models.FileField(upload_to="uploads/", null=True, blank=True)
    media_type = models.CharField(
        max_length=10,
        choices=MediaType.choices,
        default=MediaType.NONE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"[{self.role}] Message #{self.pk} in Conversation #{self.conversation_id}"


class Diagnosis(models.Model):
    """AI-generated diagnosis attached to a Conversation."""

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="diagnoses",
    )
    diagnosis_text = models.TextField()
    symptoms = models.TextField()
    recommendation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "diagnoses"

    def __str__(self) -> str:
        return f"Diagnosis #{self.pk} for Conversation #{self.conversation_id}"


class Booking(models.Model):
    """Service booking created from a chat session."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    customer_name = models.CharField(max_length=255)
    customer_contact = models.CharField(max_length=255)
    car_model = models.CharField(max_length=255)
    issue_summary = models.TextField()
    diagnosis = models.ForeignKey(
        Diagnosis,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
    )
    service = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Booking #{self.pk} — {self.customer_name} ({self.status})"
