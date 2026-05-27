from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import ROOM_NAME_VALIDATOR, Message, MessageReaction, Room


class RoomSerializer(serializers.ModelSerializer):
    # The default ModelSerializer adds a UniqueValidator on `name` because the
    # model field is unique=True. That breaks our get_or_create flow on POST,
    # so we declare `name` explicitly without it. Format is still enforced.
    name = serializers.CharField(max_length=64, validators=[ROOM_NAME_VALIDATOR])

    class Meta:
        model = Room
        fields = ("id", "name", "created_at")
        read_only_fields = ("id", "created_at")


class ReactionAggregateSerializer(serializers.Serializer):
    """Shape of one entry in the `reactions` array on a message."""

    emoji = serializers.CharField()
    count = serializers.IntegerField()
    me = serializers.BooleanField()


class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.CharField(source="sender.username", read_only=True)
    reactions = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ("id", "sender", "text", "created_at", "reactions")
        read_only_fields = fields

    @extend_schema_field(ReactionAggregateSerializer(many=True))
    def get_reactions(self, obj: Message) -> list[dict]:
        """Aggregated reactions for the message: [{emoji, count, me}].

        Operates over `prefetch_related("reactions")` data when the view
        provided it (no extra query per message). Falls back to a single
        per-call query otherwise, so the serializer is usable in shells
        and tests without a prefetch.
        """
        viewer_id = _viewer_id(self.context.get("request"))
        return ReactionAggregateSerializer(
            _aggregate_reactions(obj, viewer_id=viewer_id),
            many=True,
        ).data


class MessageReactionSerializer(serializers.Serializer):
    emoji = serializers.CharField(min_length=1, max_length=8, trim_whitespace=False)

    def validate_emoji(self, value: str) -> str:
        if any(ch.isspace() for ch in value):
            raise serializers.ValidationError("Emoji must not contain whitespace.")
        return value


# ==============================================================================
# Helpers
# ==============================================================================


def _viewer_id(request) -> int | None:
    if request is None:
        return None
    user = getattr(request, "user", None)
    return user.id if user is not None and user.is_authenticated else None


def _aggregate_reactions(message: Message, viewer_id: int | None) -> list[dict]:
    cached = getattr(message, "_prefetched_objects_cache", {}).get("reactions")
    if cached is not None:
        buckets: dict[str, dict] = {}
        for reaction in cached:
            bucket = buckets.setdefault(
                reaction.emoji, {"emoji": reaction.emoji, "count": 0, "me": False}
            )
            bucket["count"] += 1
            if viewer_id is not None and reaction.user_id == viewer_id:
                bucket["me"] = True
        return sorted(buckets.values(), key=lambda r: r["emoji"])

    buckets = {}
    for reaction in MessageReaction.objects.filter(message=message).order_by("emoji"):
        bucket = buckets.setdefault(
            reaction.emoji, {"emoji": reaction.emoji, "count": 0, "me": False}
        )
        bucket["count"] += 1
        if viewer_id is not None and reaction.user_id == viewer_id:
            bucket["me"] = True
    return list(buckets.values())
