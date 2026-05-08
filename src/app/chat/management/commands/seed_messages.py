from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from app.chat.management.commands.seed_rooms import DEMO_ROOMS
from app.chat.models import Message, Room
from app.users.management.commands.seed_users import DEMO_USERS

User = get_user_model()

MESSAGES_PER_ROOM = 18

DEMO_TEXTS = [
    "morning everyone",
    "PR is up, take a look when you have time",
    "did the migration finish on staging?",
    "lunch break, brb in 30",
    "anyone seeing 502s on the prod gateway?",
    "rebased onto main, all green",
    "moving the standup 15 min later today",
    "log lines look clean now after the loguru patch",
    "ollama just finished pulling the model",
    "ws reconnect logic is in, ready for review",
    "blocker: need a second pair of eyes on the auth flow",
    "shipping the feature flag, will toggle at noon",
]


class Command(BaseCommand):
    help = "Re-seed demo messages in demo rooms (replaces existing messages in those rooms)."

    def handle(self, *args: Any, **options: Any) -> None:
        Message.objects.filter(room__name__in=DEMO_ROOMS).delete()

        usernames = [username for username, _ in DEMO_USERS]
        users = list(User.objects.filter(username__in=usernames))
        if not users:
            self.stdout.write(
                self.style.WARNING(
                    "No demo users found. Run `make seed-users` first; nothing to seed."
                )
            )
            return

        created = 0
        rooms_touched = 0
        for room_name in DEMO_ROOMS:
            try:
                room = Room.objects.get(name=room_name)
            except Room.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Room {room_name!r} missing; skipping."))
                continue
            batch = [
                Message(
                    room=room,
                    sender=users[i % len(users)],
                    text=DEMO_TEXTS[i % len(DEMO_TEXTS)],
                )
                for i in range(MESSAGES_PER_ROOM)
            ]
            Message.objects.bulk_create(batch)
            created += len(batch)
            rooms_touched += 1

        self.stdout.write(self.style.SUCCESS(f"{created} messages across {rooms_touched} rooms."))
