from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()

DEMO_USERS = [
    ("oleksa", "oleksa@example.com"),
    ("mariia", "mariia@example.com"),
    ("bohdan", "bohdan@example.com"),
    ("kateryna", "kateryna@example.com"),
    ("taras", "taras@example.com"),
]
DEMO_PASSWORD = "pass1234"  # noqa: S105 — demo fixture, not a real credential


class Command(BaseCommand):
    help = "Create five demo users with the same password (idempotent)."

    def handle(self, *args: Any, **options: Any) -> None:
        created = 0
        for username, email in DEMO_USERS:
            _, was_created = User.objects.get_or_create(
                username=username, defaults={"email": email}
            )
            if was_created:
                user = User.objects.get(username=username)
                user.set_password(DEMO_PASSWORD)
                user.save(update_fields=["password"])
                created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo users ready: {len(DEMO_USERS)} total, {created} newly created. "
                f"Password for all: {DEMO_PASSWORD}"
            )
        )
