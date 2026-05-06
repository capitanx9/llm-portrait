from channels.generic.websocket import AsyncWebsocketConsumer


class EchoConsumer(AsyncWebsocketConsumer):
    """Smoke-test consumer: echoes every text frame back to the sender.

    Removed in PR-5 once the real chat consumer lands.
    """

    async def connect(self) -> None:
        await self.accept()

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        if text_data is not None:
            await self.send(text_data=text_data)
