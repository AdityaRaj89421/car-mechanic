"""
chatbot/serializers.py — Placeholder serializers.

Full implementations will be added in Stage 2.
"""

from rest_framework import serializers


class PlaceholderSerializer(serializers.Serializer):
    """Temporary serializer used while routes are being stubbed out."""

    message = serializers.CharField()
