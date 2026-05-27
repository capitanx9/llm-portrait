import pytest
from channels.db import database_sync_to_async
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import RefreshToken

from app.chat.models import Message, Room
from app.ws.middleware import JWTAuthMiddleware, RequestIdMiddleware
from app.ws.routing import websocket_urlpatterns
from tests.factories import UserFactory

IN_MEMORY_LAYER = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


def _app_with_origins(allowed_origins: list[str]):
    """Build an ASGI application with an explicit OriginValidator allow-list.

    The module-level `app.config.asgi.application` is bound to
    settings.WS_ALLOWED_ORIGINS at import time, so tests build their own to
    parametrise the allow-list per case. Origin-validation tests pass an
    explicit list; the rest of the suite uses ['*'] so behaviour matches the
    pre-PR baseline where any Origin (or no Origin) was accepted.
    """
    return ProtocolTypeRouter(
        {
            "websocket": OriginValidator(
                RequestIdMiddleware(JWTAuthMiddleware(URLRouter(websocket_urlpatterns))),
                allowed_origins,
            ),
        }
    )


# Default app for tests that don't care about Origin validation — accepts any.
_default_app = _app_with_origins(["*"])


@database_sync_to_async
def _make_user_and_token(username: str) -> tuple:
    """Create the user AND its token in the same sync block, so both inserts
    (User + simplejwt's OutstandingToken) commit to the test DB before the
    async event loop hands control to the consumer that will then look the
    user up. Avoids a flaky race where the consumer's User.objects.get()
    runs before the post-commit visibility of the freshly-created user.
    """
    user = UserFactory(username=username)
    token = str(RefreshToken.for_user(user).access_token)
    return user, token


async def _connect(name: str, token: str | None = None) -> WebsocketCommunicator:
    path = f"/ws/chat/{name}/"
    if token:
        path = f"{path}?token={token}"
    return WebsocketCommunicator(_default_app, path)


# ==============================================================================
# Auth
# ==============================================================================


@pytest.mark.django_db(transaction=True)
async def test_ws_rejects_connection_without_token(settings) -> None:
    settings.CHANNEL_LAYERS = IN_MEMORY_LAYER

    communicator = await _connect("general")
    connected, code = await communicator.connect()

    assert connected is False
    assert code == 4001


@pytest.mark.django_db(transaction=True)
async def test_ws_rejects_connection_with_invalid_token(settings) -> None:
    settings.CHANNEL_LAYERS = IN_MEMORY_LAYER

    communicator = await _connect("general", token="not-a-real-jwt")
    connected, code = await communicator.connect()

    assert connected is False
    assert code == 4001


@pytest.mark.django_db(transaction=True)
async def test_ws_accepts_valid_token(settings) -> None:
    settings.CHANNEL_LAYERS = IN_MEMORY_LAYER
    _, token = await _make_user_and_token("alice")

    communicator = await _connect("general", token=token)
    connected, _ = await communicator.connect()

    assert connected is True
    await communicator.disconnect()


# ==============================================================================
# Send / broadcast
# ==============================================================================


@pytest.mark.django_db(transaction=True)
async def test_ws_message_is_broadcast_to_other_clients_in_same_room(settings) -> None:
    settings.CHANNEL_LAYERS = IN_MEMORY_LAYER
    _, alice_token = await _make_user_and_token("alice")
    _, bob_token = await _make_user_and_token("bob")

    a = await _connect("general", token=alice_token)
    b = await _connect("general", token=bob_token)
    await a.connect()
    await b.connect()

    await a.send_json_to({"text": "hello bob"})

    received_a = await a.receive_json_from()
    received_b = await b.receive_json_from()

    assert received_a["text"] == "hello bob"
    assert received_a["sender"] == "alice"
    assert received_b == received_a

    await a.disconnect()
    await b.disconnect()


@pytest.mark.django_db(transaction=True)
async def test_ws_messages_in_one_room_do_not_leak_to_another(settings) -> None:
    settings.CHANNEL_LAYERS = IN_MEMORY_LAYER
    _, alice_token = await _make_user_and_token("alice")
    _, bob_token = await _make_user_and_token("bob")

    a = await _connect("general", token=alice_token)
    b = await _connect("random", token=bob_token)
    await a.connect()
    await b.connect()

    await a.send_json_to({"text": "hello"})
    await a.receive_json_from()

    assert await b.receive_nothing(timeout=0.2) is True

    await a.disconnect()
    await b.disconnect()


@pytest.mark.django_db(transaction=True)
async def test_ws_persists_message_to_db(settings) -> None:
    settings.CHANNEL_LAYERS = IN_MEMORY_LAYER
    _, alice_token = await _make_user_and_token("alice")

    a = await _connect("general", token=alice_token)
    await a.connect()
    await a.send_json_to({"text": "persisted"})
    await a.receive_json_from()
    await a.disconnect()

    count = await _count_messages("general")
    assert count == 1


@pytest.mark.django_db(transaction=True)
async def test_ws_ignores_blank_text(settings) -> None:
    settings.CHANNEL_LAYERS = IN_MEMORY_LAYER
    _, alice_token = await _make_user_and_token("alice")

    a = await _connect("general", token=alice_token)
    await a.connect()
    await a.send_json_to({"text": "   "})

    assert await a.receive_nothing(timeout=0.2) is True
    count = await _count_messages("general")
    assert count == 0
    await a.disconnect()


@pytest.mark.django_db(transaction=True)
async def test_ws_invalid_json_returns_error_frame(settings) -> None:
    """A non-JSON text frame must not tear the connection down with a
    JSONDecodeError; the consumer replies with a structured error and stays
    open so the client can recover."""
    settings.CHANNEL_LAYERS = IN_MEMORY_LAYER
    _, alice_token = await _make_user_and_token("alice")

    a = await _connect("general", token=alice_token)
    await a.connect()
    # Send a raw text frame that isn't valid JSON. Before the fix, this
    # crashed inside AsyncJsonWebsocketConsumer.decode_json and bubbled to
    # daphne; now the consumer catches it and replies on the same socket.
    await a.send_to(text_data="not json at all")

    response = await a.receive_json_from()
    assert response["error"] == "invalid_json"

    # Connection still alive — a follow-up valid message goes through.
    await a.send_json_to({"text": "after recovery"})
    follow_up = await a.receive_json_from()
    assert follow_up["text"] == "after recovery"

    await a.disconnect()


# ==============================================================================
# Origin validation
# ==============================================================================


@pytest.mark.django_db(transaction=True)
async def test_ws_rejects_disallowed_origin(settings) -> None:
    settings.CHANNEL_LAYERS = IN_MEMORY_LAYER
    _, token = await _make_user_and_token("alice")

    app = _app_with_origins(["https://app.example.com"])
    communicator = WebsocketCommunicator(
        app,
        f"/ws/chat/general/?token={token}",
        headers=[(b"origin", b"https://evil.example.com")],
    )
    connected, _ = await communicator.connect()

    assert connected is False


@pytest.mark.django_db(transaction=True)
async def test_ws_accepts_allowed_origin(settings) -> None:
    settings.CHANNEL_LAYERS = IN_MEMORY_LAYER
    _, token = await _make_user_and_token("alice")

    app = _app_with_origins(["http://localhost:5173"])
    communicator = WebsocketCommunicator(
        app,
        f"/ws/chat/general/?token={token}",
        headers=[(b"origin", b"http://localhost:5173")],
    )
    connected, _ = await communicator.connect()

    assert connected is True
    await communicator.disconnect()


# ==============================================================================
# Helpers (sync->async DB access)
# ==============================================================================


@database_sync_to_async
def _count_messages(room_name: str) -> int:
    try:
        room = Room.objects.get(name=room_name)
    except Room.DoesNotExist:
        return 0
    return Message.objects.filter(room=room).count()
