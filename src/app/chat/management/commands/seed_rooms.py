from typing import Any

from django.core.management.base import BaseCommand

from app.chat.models import Room

DEMO_ROOMS = ["general", "random", "ai-help"]


class Command(BaseCommand):
    help = "Create demo chat rooms (idempotent)."

    def handle(self, *args: Any, **options: Any) -> None:
        created = 0
        for name in DEMO_ROOMS:
            _, was_created = Room.objects.get_or_create(name=name)
            if was_created:
                created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo rooms ready: {len(DEMO_ROOMS)} total, {created} newly created."
            )
        )
