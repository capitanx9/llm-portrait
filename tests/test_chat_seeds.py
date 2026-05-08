import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from app.chat.management.commands.seed_messages import MESSAGES_PER_ROOM
from app.chat.management.commands.seed_rooms import DEMO_ROOMS
from app.chat.models import Message, Room
from app.users.management.commands.seed_users import DEMO_USERS

User = get_user_model()


@pytest.mark.django_db
def test_seed_rooms_idempotent() -> None:
    call_command("seed_rooms")
    call_command("seed_rooms")
    assert Room.objects.filter(name__in=DEMO_ROOMS).count() == len(DEMO_ROOMS)


@pytest.mark.django_db
def test_seed_messages_replaces() -> None:
    call_command("seed_users")
    call_command("seed_rooms")
    call_command("seed_messages")
    expected = len(DEMO_ROOMS) * MESSAGES_PER_ROOM
    assert Message.objects.filter(room__name__in=DEMO_ROOMS).count() == expected

    # Re-running must replace, not double up.
    call_command("seed_messages")
    assert Message.objects.filter(room__name__in=DEMO_ROOMS).count() == expected


@pytest.mark.django_db
def test_seed_all_combo() -> None:
    call_command("seed_all")
    assert User.objects.filter(username__in=[u for u, _ in DEMO_USERS]).count() == len(DEMO_USERS)
    assert Room.objects.filter(name__in=DEMO_ROOMS).count() == len(DEMO_ROOMS)
    assert (
        Message.objects.filter(room__name__in=DEMO_ROOMS).count()
        == len(DEMO_ROOMS) * MESSAGES_PER_ROOM
    )


@pytest.mark.django_db
def test_flush_demo_scope() -> None:
    # Pre-create a non-demo user, room, message — must survive flush.
    other_user = User.objects.create_user(username="other", password="other-pass")
    other_room = Room.objects.create(name="other-room")
    other_msg = Message.objects.create(room=other_room, sender=other_user, text="keep")

    call_command("seed_all")
    call_command("flush_demo")

    # Demo data gone
    assert User.objects.filter(username__in=[u for u, _ in DEMO_USERS]).count() == 0
    assert Room.objects.filter(name__in=DEMO_ROOMS).count() == 0
    assert Message.objects.filter(room__name__in=DEMO_ROOMS).count() == 0

    # Real data intact
    assert User.objects.filter(pk=other_user.pk).exists()
    assert Room.objects.filter(pk=other_room.pk).exists()
    assert Message.objects.filter(pk=other_msg.pk).exists()
