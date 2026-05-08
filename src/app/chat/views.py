import contextlib
from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Message, Room
from .serializers import MessageSerializer, RoomSerializer

DEFAULT_HISTORY_LIMIT = 50
MAX_HISTORY_LIMIT = 200


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

        qs = Message.objects.filter(room=room).select_related("sender")

        before = request.query_params.get("before")
        if before:
            with contextlib.suppress(ValueError):
                qs = qs.filter(id__lt=int(before))

        messages = list(qs[:limit])
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)
