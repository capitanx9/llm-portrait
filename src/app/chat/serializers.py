from rest_framework import serializers

from .models import ROOM_NAME_VALIDATOR, Message, Room


class RoomSerializer(serializers.ModelSerializer):
    # The default ModelSerializer adds a UniqueValidator on `name` because the
    # model field is unique=True. That breaks our get_or_create flow on POST,
    # so we declare `name` explicitly without it. Format is still enforced.
    name = serializers.CharField(max_length=64, validators=[ROOM_NAME_VALIDATOR])

    class Meta:
        model = Room
        fields = ("id", "name", "created_at")
        read_only_fields = ("id", "created_at")


class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.CharField(source="sender.username", read_only=True)

    class Meta:
        model = Message
        fields = ("id", "sender", "text", "created_at")
        read_only_fields = fields
