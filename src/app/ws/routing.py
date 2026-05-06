from django.urls import path

from .consumers import ChatConsumer

websocket_urlpatterns = [
    path("ws/chat/<str:name>/", ChatConsumer.as_asgi()),
]
