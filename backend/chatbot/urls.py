"""chatbot/urls.py — URL routing for the chatbot app."""

from django.urls import path
from . import views

urlpatterns = [
    # Chat
    path("chat/", views.chat, name="chat"),
    path("chat/<int:conversation_id>/history/", views.chat_history, name="chat-history"),
    # Media upload
    path("upload/", views.upload, name="upload"),
    # Diagnosis (stub — Stage 3 wires in Gemini)
    path("diagnosis/", views.diagnosis, name="diagnosis"),
    # Bookings
    path("booking/", views.booking_create, name="booking-create"),
    path("booking/<int:booking_id>/", views.booking_detail, name="booking-detail"),
]
