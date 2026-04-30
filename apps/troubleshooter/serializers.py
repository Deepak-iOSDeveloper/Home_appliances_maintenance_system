"""Troubleshooter Serializers"""
from rest_framework import serializers
from .models import TechnicalManual, ChatSession, Message


class TechnicalManualSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicalManual
        fields = [
            'id', 'device_type', 'brand', 'model_number',
            'title', 'content', 'chunk_index', 'word_count',
            'created_at',
        ]
        # Don't expose raw embeddings via API
        read_only_fields = ['word_count']


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            'id', 'role', 'content', 'sources',
            'metadata', 'token_count', 'created_at',
        ]


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    message_count = serializers.IntegerField(source='messages.count', read_only=True)

    class Meta:
        model = ChatSession
        fields = [
            'id', 'session_id', 'title', 'started_at', 'ended_at',
            'device_context', 'is_active', 'messages', 'message_count',
        ]


class ChatSessionListSerializer(serializers.ModelSerializer):
    """Lightweight list serializer without messages."""
    message_count = serializers.IntegerField(source='messages.count', read_only=True)

    class Meta:
        model = ChatSession
        fields = [
            'id', 'session_id', 'title', 'started_at',
            'is_active', 'message_count',
        ]


class CreateSessionSerializer(serializers.Serializer):
    """Serializer for creating a new chat session."""
    title = serializers.CharField(max_length=200, required=False, default='New Session')
    device_context = serializers.JSONField(required=False, default=dict)
