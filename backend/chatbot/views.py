"""
chatbot/views.py — Stub API views.

Each view returns a 200 placeholder response so all routes are wired
and testable. Real logic will be implemented in Stages 2–4.
"""

from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response


@api_view(["POST"])
def chat(request: Request) -> Response:
    """
    POST /api/chat/
    Stage 2 will implement: send a user message → Gemini AI → stream assistant reply.
    """
    return Response({"status": "stub", "endpoint": "chat", "message": "Chat endpoint ready."})


@api_view(["POST"])
def upload(request: Request) -> Response:
    """
    POST /api/upload/
    Stage 3 will implement: accept image/audio/video → store → return media URL.
    """
    return Response({"status": "stub", "endpoint": "upload", "message": "Upload endpoint ready."})


@api_view(["POST"])
def diagnosis(request: Request) -> Response:
    """
    POST /api/diagnosis/
    Stage 3 will implement: run AI diagnosis on conversation → return Diagnosis object.
    """
    return Response(
        {"status": "stub", "endpoint": "diagnosis", "message": "Diagnosis endpoint ready."}
    )


@api_view(["POST"])
def booking_create(request: Request) -> Response:
    """
    POST /api/booking/
    Stage 4 will implement: create a Booking from conversation context.
    """
    return Response(
        {"status": "stub", "endpoint": "booking_create", "message": "Booking create endpoint ready."}
    )


@api_view(["GET"])
def booking_detail(request: Request, booking_id: int) -> Response:
    """
    GET /api/booking/<booking_id>/
    Stage 4 will implement: retrieve a Booking by ID.
    """
    return Response(
        {
            "status": "stub",
            "endpoint": "booking_detail",
            "booking_id": booking_id,
            "message": "Booking detail endpoint ready.",
        }
    )
