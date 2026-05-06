import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from app.chat.models import Message, Room
from tests.factories import UserFactory

# ==============================================================================
# Room
# ==============================================================================


@pytest.mark.django_db
def test_room_name_must_be_unique() -> None:
    Room.objects.create(name="general")
    with pytest.raises(IntegrityError):
        Room.objects.create(name="general")


@pytest.mark.django_db
def test_room_name_validator_rejects_invalid_chars() -> None:
    room = Room(name="Bad Name!")
    with pytest.raises(ValidationError):
        room.full_clean()


@pytest.mark.django_db
def test_room_name_validator_accepts_lowercase_digits_dash() -> None:
    room = Room(name="general-2")
    room.full_clean()


# ==============================================================================
# Message
# ==============================================================================


@pytest.mark.django_db
def test_message_cascades_when_room_deleted() -> None:
    room = Room.objects.create(name="general")
    user = UserFactory()
    Message.objects.create(room=room, sender=user, text="hi")

    room.delete()

    assert Message.objects.count() == 0


@pytest.mark.django_db
def test_message_cascades_when_sender_deleted() -> None:
    room = Room.objects.create(name="general")
    user = UserFactory()
    Message.objects.create(room=room, sender=user, text="hi")

    user.delete()

    assert Message.objects.count() == 0


@pytest.mark.django_db
def test_message_default_ordering_is_newest_first() -> None:
    room = Room.objects.create(name="general")
    user = UserFactory()
    older = Message.objects.create(room=room, sender=user, text="first")
    newer = Message.objects.create(room=room, sender=user, text="second")

    messages = list(Message.objects.filter(room=room))

    assert messages[0] == newer
    assert messages[1] == older
