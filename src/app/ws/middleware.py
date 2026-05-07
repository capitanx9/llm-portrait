import uuid
from typing import Any
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from loguru import logger
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken

from app.users.models import User


@database_sync_to_async
def _get_user(user_id: int) -> User | AnonymousUser:
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """Reads ?token=<jwt> from the WebSocket query string and attaches a User
    to scope. Falls back to AnonymousUser on any error; the consumer is
    responsible for closing the connection if it requires authentication.
    """

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> Any:
        scope["user"] = await self._resolve_user(scope)
        return await super().__call__(scope, receive, send)

    @staticmethod
    async def _resolve_user(scope: dict[str, Any]) -> User | AnonymousUser:
        query = parse_qs(scope.get("query_string", b"").decode())
        token_list = query.get("token")
        if not token_list:
            return AnonymousUser()

        try:
            validated = UntypedToken(token_list[0])
        except (InvalidToken, TokenError):
            return AnonymousUser()

        user_id = validated.get("user_id")
        if user_id is None:
            return AnonymousUser()

        return await _get_user(user_id)


class RequestIdMiddleware(BaseMiddleware):
    """Generate a request id per WebSocket connection and bind it to loguru.

    HTTP requests get this from the same-named middleware in app.core; WS
    connections live longer and don't pass through Django's middleware chain,
    so we replicate the binding at the ASGI layer. Every log line emitted
    inside the consumer's lifecycle (connect, receive_json, disconnect) will
    carry `request_id=...`.
    """

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> Any:
        request_id = uuid.uuid4().hex[:12]
        scope["request_id"] = request_id
        with logger.contextualize(request_id=request_id):
            return await super().__call__(scope, receive, send)
