import json
from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from loguru import logger

from app.chat.models import Message, Room

MAX_MESSAGE_LENGTH = 4000


def _handshake_fields(scope: dict[str, Any]) -> dict[str, Any]:
    """Pull the HTTP-handshake metadata out of an ASGI scope.

    These values are only known at handshake time (the WebSocket upgrade
    is just an HTTP GET with `Upgrade: websocket`), so they're worth
    logging exactly once on `connect`. After that the connection is
    pure binary frames with no per-frame headers, and re-logging the
    handshake fields on every message would just be noise.

    Empty/missing fields are dropped from the returned dict so the
    human log doesn't spam `user_agent=None origin=None subprotocols=None`
    for minimalist clients (e.g. websocat) that don't send them. Browsers
    will fill them in.
    """
    headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
    client = scope.get("client") or ("", 0)
    fields: dict[str, Any] = {
        "client_ip": client[0],
        "user_agent": headers.get("user-agent"),
        "origin": headers.get("origin"),
        "subprotocols": scope.get("subprotocols") or None,
    }
    return {k: v for k, v in fields.items() if v}


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """Room-based chat consumer.

    Auth: JWT in ?token=<...> handled upstream by JWTAuthMiddleware
    (scope['user']). Unauthenticated connects are closed with code 4001.

    Every client in the same room joins channel group "chat_<name>", so a
    single group_send broadcasts to all of them.

    Wire protocol:
        client -> server: {"text": "hi"}
        server -> client: {"id", "sender", "text", "created_at"}

    Logging: connect/receive/disconnect emit one structured line each,
    sharing the request_id bound by app.ws.middleware.RequestIdMiddleware,
    so the full lifecycle of a single connection is greppable by id.
    """

    async def connect(self) -> None:
        user = self.scope["user"]
        if not user.is_authenticated:
            logger.info(
                "ws connect rejected: unauthenticated",
                **_handshake_fields(self.scope),
            )
            await self.close(code=4001)
            return

        self.room_name: str = self.scope["url_route"]["kwargs"]["name"]
        self.group_name: str = f"chat_{self.room_name}"
        self.room: Room = await self._get_or_create_room(self.room_name)

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(
            "ws connect accepted",
            room=self.room_name,
            user=user.username,
            **_handshake_fields(self.scope),
        )

    async def disconnect(self, code: int) -> None:
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(
            "ws disconnect",
            room=getattr(self, "room_name", None),
            user=getattr(self.scope["user"], "username", None),
            code=code,
        )

    async def receive(
        self,
        text_data: str | None = None,
        bytes_data: bytes | None = None,
        **kwargs: Any,
    ) -> None:
        # Override the base class so a non-JSON payload (`'\n'`, plain text,
        # whatever the client typo'd) returns a structured error frame
        # instead of bubbling a JSONDecodeError up to daphne and tearing
        # the connection down with a 500-style traceback. Anything else is
        # delegated to the JSON path as usual.
        if text_data is None:
            return
        try:
            content = json.loads(text_data)
        except json.JSONDecodeError as exc:
            logger.warning("ws invalid json", error=str(exc), preview=text_data[:120])
            await self.send_json({"error": "invalid_json", "detail": str(exc)})
            return
        await self.receive_json(content, **kwargs)

    async def receive_json(self, content: dict[str, Any], **kwargs: Any) -> None:
        text = (content.get("text") or "").strip()
        if not text:
            return
        text = text[:MAX_MESSAGE_LENGTH]

        try:
            message = await self._save_message(self.room, self.scope["user"], text)
        except Exception:
            # Any DB / channel-layer failure is logged with the full
            # diagnose-traceback under the connection's request_id, so the
            # operator can correlate it with the access log entry that
            # accepted the message.
            logger.exception("ws message handling failed")
            await self.send_json({"error": "internal", "detail": "message not saved"})
            return

        logger.info(
            "ws message",
            room=self.room_name,
            user=self.scope["user"].username,
            length=len(text),
            frame_type="text",
            message_id=message.id,
        )
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
