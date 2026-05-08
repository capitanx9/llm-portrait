from typing import Any

from rest_framework import serializers

ALLOWED_LANGS = ("ru", "en", "uk", "fr", "es", "de")
ALLOWED_ACTIONS = ("translate", "summarize")


class ConversationTurnSerializer(serializers.Serializer):
    role = serializers.CharField(max_length=32)
    content = serializers.CharField(max_length=4000)


class ProcessRequestSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=ALLOWED_ACTIONS)
    message = serializers.CharField(required=False, max_length=4000, allow_blank=False)
    target_language = serializers.ChoiceField(choices=ALLOWED_LANGS, required=False)
    conversation = serializers.ListField(
        child=ConversationTurnSerializer(),
        required=False,
        min_length=1,
        max_length=200,
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        action = attrs["action"]
        if action == "translate":
            missing = [k for k in ("message", "target_language") if k not in attrs]
            if missing:
                raise serializers.ValidationError(
                    {k: "This field is required for translate." for k in missing}
                )
        elif action == "summarize" and "conversation" not in attrs:
            raise serializers.ValidationError(
                {"conversation": "This field is required for summarize."}
            )
        return attrs


class ProcessResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=ALLOWED_ACTIONS)
    source_language = serializers.CharField()
    translation = serializers.CharField(required=False)
    summary = serializers.CharField(required=False)
