from channels.testing import WebsocketCommunicator

from app.config.asgi import application

# Channels tests must not depend on Redis. Override the channel layer to the
# in-memory backend so consumer lifecycle doesn't try to talk to a real broker.
IN_MEMORY_LAYER = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


# ==============================================================================
# Echo
# ==============================================================================


async def test_echo_consumer_returns_what_it_received(settings) -> None:
    settings.CHANNEL_LAYERS = IN_MEMORY_LAYER

    communicator = WebsocketCommunicator(application, "/ws/echo/")
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_to(text_data="ping")
    response = await communicator.receive_from()
    assert response == "ping"

    await communicator.disconnect()


async def test_echo_consumer_handles_multiple_frames(settings) -> None:
    settings.CHANNEL_LAYERS = IN_MEMORY_LAYER

    communicator = WebsocketCommunicator(application, "/ws/echo/")
    connected, _ = await communicator.connect()
    assert connected

    for msg in ["one", "two", "three"]:
        await communicator.send_to(text_data=msg)
        response = await communicator.receive_from()
        assert response == msg

    await communicator.disconnect()
