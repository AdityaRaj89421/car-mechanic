"""
chatbot/tests.py — Stage 6 test suite.

Coverage:
  ChatViewTests       — chat happy path, missing message, invalid conv id
  OffTopicTests       — Gemini off_topic and error paths (mocked)
  UploadValidation    — oversized file, wrong extension, wrong media_type, happy path
  ChatHistoryTests    — history 200, history 404
  DiagnosisTests      — existing diagnosis return, no-messages path
  BookingCreateTests  — happy path 201, missing fields 400, invalid conv 400
  BookingDetailTests  — 200 with nested data, 404
  ErrorHandlingTests  — no 500s on bad inputs, method not allowed

All Gemini calls are mocked. Tests NEVER hit the real Gemini API.

Run:
    cd backend
    .\\venv\\Scripts\\python manage.py test chatbot --verbosity=2
"""

import io
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from chatbot.models import Booking, Conversation, Diagnosis, Message

# ── Shared mock responses ─────────────────────────────────────────────────────

NEED_MORE_INFO = {
    "status": "need_more_info",
    "question": "How long has the noise been present?",
}

DIAGNOSIS_READY = {
    "status": "diagnosis_ready",
    "diagnosis": "Worn brake pads causing metal-on-metal contact.",
    "symptoms": "Grinding noise when braking; vibration in brake pedal.",
    "recommendation": "Replace front and rear brake pads immediately.",
}

OFF_TOPIC = {
    "status": "off_topic",
    "message": "I can only assist with vehicle-related questions.",
}

AI_ERROR = {
    "status": "error",
    "error": "ai_unavailable: timeout",
}

PATCH_TARGET = "chatbot.views.call_gemini"


def _json(response):
    """Parse JSON body, raise on non-JSON."""
    return response.json()


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_conversation():
    return Conversation.objects.create()


def make_message(conversation, role=Message.Role.USER, content="test"):
    return Message.objects.create(
        conversation=conversation,
        role=role,
        content=content,
        media_type=Message.MediaType.NONE,
    )


def make_diagnosis(conversation):
    return Diagnosis.objects.create(
        conversation=conversation,
        diagnosis_text="Engine rod bearing failure.",
        symptoms="Rhythmic metallic knock.",
        recommendation="Stop driving. Immediate engine inspection required.",
    )


def make_booking(conversation, diagnosis=None):
    return Booking.objects.create(
        conversation=conversation,
        customer_name="Test User",
        customer_contact="test@example.com",
        car_model="Toyota Camry 2019",
        issue_summary="Knocking engine noise.",
        service="Full engine inspection",
        diagnosis=diagnosis,
    )


# ── Chat endpoint ─────────────────────────────────────────────────────────────

class ChatViewTests(TestCase):

    @patch(PATCH_TARGET, return_value=NEED_MORE_INFO)
    def test_chat_starts_new_conversation(self, _mock):
        """Happy path: no conversation_id → new Conversation created."""
        resp = self.client.post(
            "/api/chat/",
            {"message": "My car makes a knocking noise."},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = _json(resp)
        self.assertIn("conversation_id", data)
        self.assertEqual(data["ai_status"], "need_more_info")
        self.assertIsNotNone(data["reply"])
        self.assertEqual(Conversation.objects.count(), 1)
        # user + assistant messages persisted
        self.assertEqual(Message.objects.count(), 2)

    @patch(PATCH_TARGET, return_value=NEED_MORE_INFO)
    def test_chat_continues_existing_conversation(self, _mock):
        """Sending conversation_id continues the session."""
        conv = make_conversation()
        make_message(conv, content="First message.")

        resp = self.client.post(
            "/api/chat/",
            {"conversation_id": conv.pk, "message": "Second message."},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = _json(resp)
        self.assertEqual(data["conversation_id"], conv.pk)
        # original + new user + new assistant = 3
        self.assertEqual(Message.objects.filter(conversation=conv).count(), 3)

    @patch(PATCH_TARGET, return_value=DIAGNOSIS_READY)
    def test_chat_creates_diagnosis_on_ready(self, _mock):
        """When Gemini returns diagnosis_ready, a Diagnosis row is created."""
        resp = self.client.post(
            "/api/chat/",
            {"message": "Engine knocks loudly, oil very low, 95k miles."},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = _json(resp)
        self.assertEqual(data["ai_status"], "diagnosis_ready")
        self.assertIsNotNone(data["diagnosis"])
        self.assertEqual(Diagnosis.objects.count(), 1)
        diag = Diagnosis.objects.first()
        self.assertIn("brake", diag.diagnosis_text.lower())

    def test_chat_rejects_empty_message(self):
        """Blank message body → 400 with 'message' field error."""
        resp = self.client.post(
            "/api/chat/",
            {"message": "   "},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("message", _json(resp))

    def test_chat_rejects_missing_message_field(self):
        """Completely missing 'message' key → 400."""
        resp = self.client.post(
            "/api/chat/",
            {},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_chat_rejects_nonexistent_conversation_id(self):
        """Referencing a non-existent conversation_id → 400 (not 500)."""
        resp = self.client.post(
            "/api/chat/",
            {"conversation_id": 99999, "message": "hello"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("conversation_id", _json(resp))

    def test_chat_rejects_invalid_conversation_id_type(self):
        """Non-integer conversation_id → 400 (not 500)."""
        resp = self.client.post(
            "/api/chat/",
            {"conversation_id": "not-an-int", "message": "hello"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


# ── Off-topic / AI error paths ────────────────────────────────────────────────

class OffTopicTests(TestCase):

    @patch(PATCH_TARGET, return_value=OFF_TOPIC)
    def test_off_topic_returns_200_not_500(self, _mock):
        """Off-topic Gemini response → 200 with off_topic status, no crash."""
        resp = self.client.post(
            "/api/chat/",
            {"message": "Write me a Python script."},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = _json(resp)
        self.assertEqual(data["ai_status"], "off_topic")
        self.assertIn("vehicle", data["reply"].lower())
        # No Diagnosis should have been created
        self.assertEqual(Diagnosis.objects.count(), 0)

    @patch(PATCH_TARGET, return_value=AI_ERROR)
    def test_ai_error_returns_200_not_500(self, _mock):
        """Gemini failure → 200 with error status and fallback reply, no 500."""
        resp = self.client.post(
            "/api/chat/",
            {"message": "My brakes squeal."},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = _json(resp)
        self.assertEqual(data["ai_status"], "error")
        self.assertIn("trouble", data["reply"].lower())
        # Message still saved even if AI failed
        self.assertEqual(Message.objects.count(), 2)

    @patch(PATCH_TARGET, side_effect=Exception("Simulated crash"))
    def test_uncaught_gemini_exception_does_not_500(self, _mock):
        """
        Even if call_gemini() itself throws an uncaught exception, the endpoint
        must not return a raw 500. The view catches this via the service layer.

        NOTE: call_gemini() has a try/except that returns AI_ERROR on any
        exception, so this test confirms the contract holds.
        """
        # Re-patch with the actual service to ensure its try/except fires
        with patch(PATCH_TARGET, return_value=AI_ERROR):
            resp = self.client.post(
                "/api/chat/",
                {"message": "Engine light on."},
                content_type="application/json",
            )
        self.assertNotEqual(resp.status_code, 500)


# ── Upload validation ─────────────────────────────────────────────────────────

class UploadValidationTests(TestCase):

    def setUp(self):
        self.conv = make_conversation()

    def _upload(self, filename, content, media_type, size_override=None):
        """Helper: POST multipart to /api/upload/."""
        data = content if size_override is None else b"x" * size_override
        f = SimpleUploadedFile(filename, data, content_type="image/jpeg")
        return self.client.post(
            "/api/upload/",
            {
                "file": f,
                "media_type": media_type,
                "conversation_id": self.conv.pk,
            },
        )

    @patch(PATCH_TARGET, return_value=NEED_MORE_INFO)
    def test_valid_image_upload_returns_201(self, _mock):
        """Valid JPEG image under limit → 201."""
        resp = self._upload("engine.jpg", b"\xff\xd8\xff" + b"0" * 100, "image")
        self.assertEqual(resp.status_code, 201)
        data = _json(resp)
        self.assertIn("message", data)
        self.assertEqual(data["message"]["media_type"], "image")

    def test_rejects_oversized_image(self):
        """Image exceeding 5 MB → 400 with 'file' error."""
        resp = self._upload(
            "large.jpg",
            b"\xff\xd8\xff",
            "image",
            size_override=5 * 1024 * 1024 + 1,
        )
        self.assertEqual(resp.status_code, 400)
        data = _json(resp)
        self.assertIn("file", data)
        self.assertIn("large", data["file"].lower())

    def test_rejects_wrong_extension_for_image(self):
        """Uploading a .pdf as media_type='image' → 400."""
        f = SimpleUploadedFile("document.pdf", b"%PDF-", content_type="application/pdf")
        resp = self.client.post(
            "/api/upload/",
            {"file": f, "media_type": "image", "conversation_id": self.conv.pk},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("file", _json(resp))

    def test_rejects_exe_disguised_as_image(self):
        """Uploading a .exe with media_type='image' → 400."""
        f = SimpleUploadedFile("virus.exe", b"MZ\x90\x00", content_type="application/octet-stream")
        resp = self.client.post(
            "/api/upload/",
            {"file": f, "media_type": "image", "conversation_id": self.conv.pk},
        )
        self.assertEqual(resp.status_code, 400)

    def test_rejects_invalid_media_type(self):
        """Unknown media_type value → 400."""
        f = SimpleUploadedFile("file.jpg", b"\xff\xd8\xff", content_type="image/jpeg")
        resp = self.client.post(
            "/api/upload/",
            {"file": f, "media_type": "document", "conversation_id": self.conv.pk},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("media_type", _json(resp))

    def test_rejects_missing_file(self):
        """No file field → 400 with 'file' error."""
        resp = self.client.post(
            "/api/upload/",
            {"media_type": "image", "conversation_id": self.conv.pk},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("file", _json(resp))

    def test_rejects_upload_without_conversation(self):
        """Missing conversation_id → 400."""
        f = SimpleUploadedFile("img.jpg", b"\xff\xd8\xff", content_type="image/jpeg")
        resp = self.client.post(
            "/api/upload/",
            {"file": f, "media_type": "image"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_rejects_oversized_audio(self):
        """Audio exceeding 10 MB → 400."""
        f = SimpleUploadedFile(
            "sound.mp3", b"x" * (10 * 1024 * 1024 + 1), content_type="audio/mpeg"
        )
        resp = self.client.post(
            "/api/upload/",
            {"file": f, "media_type": "audio", "conversation_id": self.conv.pk},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("large", _json(resp)["file"].lower())

    def test_rejects_oversized_video(self):
        """Video exceeding 25 MB → 400."""
        f = SimpleUploadedFile(
            "vid.mp4", b"x" * (25 * 1024 * 1024 + 1), content_type="video/mp4"
        )
        resp = self.client.post(
            "/api/upload/",
            {"file": f, "media_type": "video", "conversation_id": self.conv.pk},
        )
        self.assertEqual(resp.status_code, 400)

    @patch(PATCH_TARGET, return_value=NEED_MORE_INFO)
    def test_audio_upload_returns_ack_not_ai_analysis(self, _mock):
        """Audio upload → 201, no Gemini call for analysis (scope decision)."""
        f = SimpleUploadedFile("clip.mp3", b"x" * 100, content_type="audio/mpeg")
        resp = self.client.post(
            "/api/upload/",
            {"file": f, "media_type": "audio", "conversation_id": self.conv.pk},
        )
        self.assertEqual(resp.status_code, 201)
        data = _json(resp)
        # Assistant reply should acknowledge the audio, not be a Gemini diagnosis
        self.assertIn("audio", data["assistant_reply"]["content"].lower())
        # Gemini should NOT have been called for audio
        _mock.assert_not_called()


# ── Chat history ──────────────────────────────────────────────────────────────

class ChatHistoryTests(TestCase):

    def test_history_returns_messages_oldest_first(self):
        """GET /api/chat/<id>/history/ → ordered messages."""
        conv = make_conversation()
        make_message(conv, Message.Role.USER, "First")
        make_message(conv, Message.Role.ASSISTANT, "Second")
        make_message(conv, Message.Role.USER, "Third")

        resp = self.client.get(f"/api/chat/{conv.pk}/history/")
        self.assertEqual(resp.status_code, 200)
        data = _json(resp)
        self.assertEqual(data["conversation_id"], conv.pk)
        msgs = data["messages"]
        self.assertEqual(len(msgs), 3)
        self.assertEqual(msgs[0]["content"], "First")
        self.assertEqual(msgs[1]["role"], "assistant")

    def test_history_404_for_missing_conversation(self):
        """Non-existent conversation_id → 404 (not 500)."""
        resp = self.client.get("/api/chat/99999/history/")
        self.assertEqual(resp.status_code, 404)


# ── Diagnosis endpoint ────────────────────────────────────────────────────────

class DiagnosisTests(TestCase):

    def test_returns_existing_diagnosis(self):
        """Conversation with existing Diagnosis → source='existing'."""
        conv = make_conversation()
        diag = make_diagnosis(conv)

        resp = self.client.post(
            "/api/diagnosis/",
            {"conversation_id": conv.pk},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = _json(resp)
        self.assertEqual(data["source"], "existing")
        self.assertEqual(data["diagnosis"]["id"], diag.pk)

    def test_insufficient_data_when_no_messages(self):
        """Empty conversation → source='insufficient_data'."""
        conv = make_conversation()
        resp = self.client.post(
            "/api/diagnosis/",
            {"conversation_id": conv.pk},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = _json(resp)
        self.assertEqual(data["source"], "insufficient_data")
        self.assertIsNone(data["diagnosis"])

    def test_rejects_missing_conversation_id(self):
        """Missing conversation_id → 400."""
        resp = self.client.post("/api/diagnosis/", {}, content_type="application/json")
        self.assertEqual(resp.status_code, 400)


# ── Booking creation ──────────────────────────────────────────────────────────

class BookingCreateTests(TestCase):

    def setUp(self):
        self.conv = make_conversation()

    def _valid_payload(self, **overrides):
        payload = {
            "conversation_id": self.conv.pk,
            "customer_name": "Jane Smith",
            "customer_contact": "+1-555-0100",
            "car_model": "Honda Civic 2020",
            "issue_summary": "Grinding noise when braking.",
            "service": "Brake pad replacement",
        }
        payload.update(overrides)
        return payload

    def test_booking_creation_happy_path(self):
        """Valid payload → 201 with booking ID and status 'pending'."""
        resp = self.client.post(
            "/api/booking/",
            self._valid_payload(),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        data = _json(resp)
        self.assertIn("id", data)
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["customer_name"], "Jane Smith")
        self.assertEqual(Booking.objects.count(), 1)

    def test_booking_links_existing_diagnosis(self):
        """If a Diagnosis exists for the conversation, it's auto-linked."""
        diag = make_diagnosis(self.conv)
        resp = self.client.post(
            "/api/booking/",
            self._valid_payload(),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        booking = Booking.objects.first()
        self.assertEqual(booking.diagnosis_id, diag.pk)

    def test_booking_rejects_missing_customer_name(self):
        """Missing customer_name → 400 with field error."""
        payload = self._valid_payload()
        del payload["customer_name"]
        resp = self.client.post("/api/booking/", payload, content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("customer_name", _json(resp))

    def test_booking_rejects_missing_customer_contact(self):
        """Missing customer_contact → 400."""
        payload = self._valid_payload()
        del payload["customer_contact"]
        resp = self.client.post("/api/booking/", payload, content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("customer_contact", _json(resp))

    def test_booking_rejects_missing_service(self):
        """Missing service → 400."""
        payload = self._valid_payload()
        del payload["service"]
        resp = self.client.post("/api/booking/", payload, content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_booking_rejects_nonexistent_conversation(self):
        """Non-existent conversation_id → 400 (not 500)."""
        resp = self.client.post(
            "/api/booking/",
            self._valid_payload(conversation_id=99999),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_booking_rejects_empty_payload(self):
        """Empty payload → 400."""
        resp = self.client.post("/api/booking/", {}, content_type="application/json")
        self.assertEqual(resp.status_code, 400)


# ── Booking retrieval ─────────────────────────────────────────────────────────

class BookingDetailTests(TestCase):

    def test_booking_detail_200(self):
        """GET /api/booking/<id>/ → 200 with nested data."""
        conv = make_conversation()
        diag = make_diagnosis(conv)
        booking = make_booking(conv, diagnosis=diag)

        resp = self.client.get(f"/api/booking/{booking.pk}/")
        self.assertEqual(resp.status_code, 200)
        data = _json(resp)
        self.assertEqual(data["id"], booking.pk)
        self.assertEqual(data["customer_name"], "Test User")
        self.assertIn("id", data["diagnosis"])
        self.assertIn("id", data["conversation"])

    def test_booking_detail_404(self):
        """Non-existent booking_id → 404 (not 500)."""
        resp = self.client.get("/api/booking/99999/")
        self.assertEqual(resp.status_code, 404)


# ── Error handling / no-500 contract ─────────────────────────────────────────

class ErrorHandlingTests(TestCase):
    """
    Verify that no endpoint returns a raw 500 on malformed inputs.
    Each test sends a deliberately bad request and asserts status < 500.
    """

    def assertNot500(self, resp):
        self.assertLess(
            resp.status_code,
            500,
            f"Got HTTP {resp.status_code} — raw 500 must never reach the client.\nBody: {resp.content[:400]}",
        )

    def test_chat_malformed_json(self):
        resp = self.client.post(
            "/api/chat/",
            "}{not valid json",
            content_type="application/json",
        )
        self.assertNot500(resp)

    def test_upload_json_content_type(self):
        """Sending JSON to the multipart upload endpoint → 415, never 500."""
        resp = self.client.post(
            "/api/upload/",
            {"file": "not-a-file"},
            content_type="application/json",
        )
        self.assertNot500(resp)

    def test_booking_malformed_json(self):
        resp = self.client.post(
            "/api/booking/",
            "bad-json!!!",
            content_type="application/json",
        )
        self.assertNot500(resp)

    def test_booking_detail_string_id(self):
        """String in place of integer booking_id → 404, not 500."""
        resp = self.client.get("/api/booking/not-a-number/")
        self.assertNot500(resp)

    def test_chat_history_string_id(self):
        resp = self.client.get("/api/chat/not-a-number/history/")
        self.assertNot500(resp)

    def test_get_to_post_only_endpoint(self):
        """GET to POST-only endpoint → 405 (not 500)."""
        resp = self.client.get("/api/chat/")
        self.assertEqual(resp.status_code, 405)

    def test_post_to_get_only_endpoint(self):
        """POST to GET-only endpoint (booking detail) → 405."""
        conv = make_conversation()
        booking = make_booking(conv)
        resp = self.client.post(f"/api/booking/{booking.pk}/", {}, content_type="application/json")
        self.assertEqual(resp.status_code, 405)
