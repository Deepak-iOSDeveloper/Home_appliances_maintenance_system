"""
WebSocket Consumer — Real-time streaming chat interface.

Handles WebSocket connections for the troubleshooter chatbot.
Streams LLM response chunks back to the React frontend.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .services import run_troubleshooter


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Async WebSocket consumer for the ARHIS neural chatbot.

    Protocol:
      Client → Server: {"query": "Check my smart lock"}
      Server → Client: {"type": "chunk", "content": "## Device..."} (multiple)
      Server → Client: {"type": "sources", "content": [...]}
      Server → Client: {"type": "trace", "content": [...]}
      Server → Client: {"type": "done", "content": {...}}
    """

    async def connect(self):
        """Accept WebSocket connection and join session group."""
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.group_name = f'chat_{self.session_id}'

        # Join channel group
        await self.channel_layer.group_add(
            self.group_name, self.channel_name
        )
        await self.accept()

        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'content': {
                'session_id': self.session_id,
                'message': 'Connected to ARHIS Neural Troubleshooter.'
            }
        }))

    async def disconnect(self, close_code):
        """Leave channel group on disconnect."""
        await self.channel_layer.group_discard(
            self.group_name, self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming message — run troubleshooter pipeline."""
        try:
            data = json.loads(text_data)
            query = data.get('query', '').strip()

            if not query:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'content': 'Empty query. Please ask a question.'
                }))
                return

            # Stream response chunks back to client
            async for event in run_troubleshooter(self.session_id, query):
                await self.send(text_data=json.dumps(event))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'content': 'Invalid JSON format.'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'content': f'Server error: {str(e)}'
            }))
