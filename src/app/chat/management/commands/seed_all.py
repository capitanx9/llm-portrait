from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run seed_users, seed_rooms, and seed_messages in order."

    def handle(self, *args: Any, **options: Any) -> None:
        call_command("seed_users")
        call_command("seed_rooms")
        call_command("seed_messages")
