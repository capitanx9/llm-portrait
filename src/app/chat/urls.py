from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("rooms/", views.RoomListCreateView.as_view(), name="rooms"),
    path("rooms/<str:name>/messages/", views.RoomMessagesView.as_view(), name="room-messages"),
    path(
        "messages/<int:pk>/reactions/",
        views.MessageReactionsView.as_view(),
        name="message-reactions",
    ),
    path(
        "messages/<int:pk>/reactions/<str:emoji>/",
        views.MessageReactionDetailView.as_view(),
        name="message-reaction-detail",
    ),
]
