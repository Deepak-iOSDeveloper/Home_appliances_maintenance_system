"""Troubleshooter WebSocket Routing"""
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/chat/<str:session_id>/', consumers.ChatConsumer.as_asgi()),
]
