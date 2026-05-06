from channels.testing import WebsocketCommunicator

from app.config.asgi import application

# ==============================================================================
# Echo
# ==============================================================================


async def test_echo_consumer_returns_what_it_received() -> None:
    communicator = WebsocketCommunicator(application, "/ws/echo/")
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_to(text_data="ping")
    response = await communicator.receive_from()
    assert response == "ping"

    await communicator.disconnect()


async def test_echo_consumer_handles_multiple_frames() -> None:
    communicator = WebsocketCommunicator(application, "/ws/echo/")
    connected, _ = await communicator.connect()
    assert connected

    for msg in ["one", "two", "three"]:
        await communicator.send_to(text_data=msg)
        response = await communicator.receive_from()
        assert response == msg

    await communicator.disconnect()
