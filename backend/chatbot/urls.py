"""chatbot/urls.py — URL routing for the chatbot app."""

from django.urls import path
from . import views

urlpatterns = [
    path("chat/", views.chat, name="chat"),
    path("upload/", views.upload, name="upload"),
    path("diagnosis/", views.diagnosis, name="diagnosis"),
    path("booking/", views.booking_create, name="booking-create"),
    path("booking/<int:booking_id>/", views.booking_detail, name="booking-detail"),
]
