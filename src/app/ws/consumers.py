from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from app.chat.models import Message, Room

MAX_MESSAGE_LENGTH = 4000


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """Room-based chat consumer.

    Auth: JWT in ?token=<...> handled upstream by JWTAuthMiddleware
    (scope['user']). Unauthenticated connects are closed with code 4001.

    Every client in the same room joins channel group "chat_<name>", so a
    single group_send broadcasts to all of them.

    Wire protocol:
        client -> server: {"text": "hi"}
        server -> client: {"id", "sender", "text", "created_at"}
    """

    async def connect(self) -> None:
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=4001)
            return

        self.room_name: str = self.scope["url_route"]["kwargs"]["name"]
        self.group_name: str = f"chat_{self.room_name}"
        self.room: Room = await self._get_or_create_room(self.room_name)

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code: int) -> None:
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content: dict[str, Any], **kwargs: Any) -> None:
        text = (content.get("text") or "").strip()
        if not text:
            return
        text = text[:MAX_MESSAGE_LENGTH]

        message = await self._save_message(self.room, self.scope["user"], text)
        payload = {
            "id": message.id,
            "sender": self.scope["user"].username,
            "text": message.text,
            "created_at": message.created_at.isoformat(),
        }
        await self.channel_layer.group_send(
            self.group_name, {"type": "chat.message", "payload": payload}
        )

    async def chat_message(self, event: dict[str, Any]) -> None:
        await self.send_json(event["payload"])

    @staticmethod
    @database_sync_to_async
    def _get_or_create_room(name: str) -> Room:
        room, _ = Room.objects.get_or_create(name=name)
        return room

    @staticmethod
    @database_sync_to_async
    def _save_message(room: Room, sender: Any, text: str) -> Message:
        return Message.objects.create(room=room, sender=sender, text=text)
