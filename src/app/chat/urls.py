from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("rooms/", views.RoomListCreateView.as_view(), name="rooms"),
    path("rooms/<str:name>/messages/", views.RoomMessagesView.as_view(), name="room-messages"),
]
