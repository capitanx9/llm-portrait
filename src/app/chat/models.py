from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

ROOM_NAME_VALIDATOR = RegexValidator(
    regex=r"^[a-z0-9-]+$",
    message="Имя комнаты может содержать только латинские буквы, цифры и дефис.",
)


class Room(models.Model):
    name = models.CharField(max_length=64, unique=True, validators=[ROOM_NAME_VALIDATOR])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Message(models.Model):
    room = models.ForeignKey(Room, related_name="messages", on_delete=models.CASCADE)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="messages", on_delete=models.CASCADE
    )
    text = models.CharField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["room", "-created_at"])]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.sender.username} in {self.room.name}: {self.text[:40]}"


class MessageReaction(models.Model):
    message = models.ForeignKey(Message, related_name="reactions", on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="reactions", on_delete=models.CASCADE
    )
    # 8 chars fits emoji-with-modifiers (ZWJ sequences like 👨‍👩‍👧).
    emoji = models.CharField(max_length=8)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("message", "user", "emoji")]
        indexes = [models.Index(fields=["message", "emoji"])]

    def __str__(self) -> str:
        return f"{self.user.username} {self.emoji} on message #{self.message_id}"
