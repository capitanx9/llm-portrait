import contextlib
from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from app.chat.management.commands.seed_rooms import DEMO_ROOMS

from .models import Message, MessageReaction, Room
from .serializers import MessageReactionSerializer, MessageSerializer, RoomSerializer

DEFAULT_HISTORY_LIMIT = 50
MAX_HISTORY_LIMIT = 200


@extend_schema(
    examples=[
        OpenApiExample(
            "Create demo room",
            value={"name": DEMO_ROOMS[0]},
            request_only=True,
        ),
    ],
)
class RoomListCreateView(generics.ListCreateAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room, created = Room.objects.get_or_create(name=serializer.validated_data["name"])
        return Response(
            RoomSerializer(room).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class RoomMessagesView(generics.GenericAPIView):
    serializer_class = MessageSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    f"Page size, capped at {MAX_HISTORY_LIMIT}. "
                    f"Default {DEFAULT_HISTORY_LIMIT}."
                ),
            ),
            OpenApiParameter(
                name="before",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Return only messages with id < before (cursor pagination).",
            ),
        ],
        responses={200: MessageSerializer(many=True)},
    )
    def get(self, request: Request, name: str) -> Response:
        room = get_object_or_404(Room, name=name)

        try:
            raw_limit = int(request.query_params.get("limit", DEFAULT_HISTORY_LIMIT))
            limit = min(raw_limit, MAX_HISTORY_LIMIT)
        except ValueError:
            limit = DEFAULT_HISTORY_LIMIT

        qs = (
            Message.objects.filter(room=room).select_related("sender").prefetch_related("reactions")
        )

        before = request.query_params.get("before")
        if before:
            with contextlib.suppress(ValueError):
                qs = qs.filter(id__lt=int(before))

        messages = list(qs[:limit])
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)


class MessageReactionsView(APIView):
    """POST /api/chat/messages/<pk>/reactions/ — add a reaction.

    Idempotent: a second POST with the same emoji from the same user
    returns 200 instead of 201 and does not create a duplicate row
    (enforced by the unique_together on the model).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = MessageReactionSerializer

    @extend_schema(
        request=MessageReactionSerializer,
        responses={201: MessageReactionSerializer, 200: MessageReactionSerializer},
    )
    def post(self, request: Request, pk: int) -> Response:
        message = get_object_or_404(Message, pk=pk)
        serializer = MessageReactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        emoji = serializer.validated_data["emoji"]

        _, created = MessageReaction.objects.get_or_create(
            message=message, user=request.user, emoji=emoji
        )
        return Response(
            {"emoji": emoji},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MessageReactionDetailView(APIView):
    """DELETE /api/chat/messages/<pk>/reactions/<emoji>/ — remove own reaction.

    Idempotent: 204 even when the reaction doesn't exist, so the client can
    issue a blind DELETE on chip click without first checking state.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={204: None})
    def delete(self, request: Request, pk: int, emoji: str) -> Response:
        MessageReaction.objects.filter(message_id=pk, user=request.user, emoji=emoji).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
