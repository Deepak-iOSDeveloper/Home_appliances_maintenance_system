"""
Troubleshooter Models — Neural Chatbot
Stores technical manuals for RAG, chat sessions, and messages.
"""
import uuid
from django.db import models


class TechnicalManual(models.Model):
    """
    Chunked technical manual content for RAG semantic search.
    Each row is a chunk of a device manual with its embedding.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_type = models.CharField(max_length=50)
    brand = models.CharField(max_length=100)
    model_number = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=300, help_text='Section/chapter title')
    content = models.TextField(help_text='Manual text content (chunk)')
    chunk_index = models.IntegerField(default=0, help_text='Position within the full manual')
    embedding = models.BinaryField(
        null=True, blank=True,
        help_text='Serialized embedding vector for FAISS'
    )
    word_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['device_type', 'brand', 'chunk_index']
        indexes = [
            models.Index(fields=['device_type']),
            models.Index(fields=['brand']),
        ]

    def save(self, *args, **kwargs):
        self.word_count = len(self.content.split())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.brand} {self.model_number}] {self.title} (chunk {self.chunk_index})"


class ChatSession(models.Model):
    """A troubleshooting chat session."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.CharField(
        max_length=100, unique=True, db_index=True,
        help_text='External session identifier'
    )
    title = models.CharField(max_length=200, blank=True, default='New Session')
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    device_context = models.JSONField(
        default=dict, blank=True,
        help_text='Devices being discussed in this session'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"Session {self.session_id[:8]} — {self.title}"


class Message(models.Model):
    """A single message in a chat session."""

    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    sources = models.JSONField(
        default=list, blank=True,
        help_text='Manual sections cited in this response'
    )
    metadata = models.JSONField(
        default=dict, blank=True,
        help_text='Additional context (device data, confidence, etc.)'
    )
    token_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        preview = self.content[:60] + '...' if len(self.content) > 60 else self.content
        return f"[{self.role}] {preview}"
