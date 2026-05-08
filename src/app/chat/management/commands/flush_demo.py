from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from app.chat.management.commands.seed_rooms import DEMO_ROOMS
from app.chat.models import Message, Room
from app.users.management.commands.seed_users import DEMO_USERS

User = get_user_model()


class Command(BaseCommand):
    help = "Remove all seeded users, rooms, and messages. Leaves real data alone."

    def handle(self, *args: Any, **options: Any) -> None:
        # Count BEFORE deleting because Django's QuerySet.delete() returns
        # the total of all cascaded rows (Message + UserProfile + …), not
        # the number of rows in the queryset itself. Pre-counting keeps the
        # report honest.
        msg_count = Message.objects.filter(room__name__in=DEMO_ROOMS).count()
        room_count = Room.objects.filter(name__in=DEMO_ROOMS).count()
        usernames = [username for username, _ in DEMO_USERS]
        user_count = User.objects.filter(username__in=usernames).count()

        Message.objects.filter(room__name__in=DEMO_ROOMS).delete()
        Room.objects.filter(name__in=DEMO_ROOMS).delete()
        User.objects.filter(username__in=usernames).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Flushed: {msg_count} messages, {room_count} rooms, {user_count} users."
            )
        )
