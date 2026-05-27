import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from app.chat.models import Message, MessageReaction, Room
from tests.factories import UserFactory

# ==============================================================================
# Helpers
# ==============================================================================


def _auth_client(user) -> APIClient:
    client = APIClient()
    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def _make_message(room_name: str = "general") -> Message:
    room, _ = Room.objects.get_or_create(name=room_name)
    sender = UserFactory(username="sender")
    return Message.objects.create(room=room, sender=sender, text="hi")


# ==============================================================================
# POST /api/chat/messages/<pk>/reactions/
# ==============================================================================


@pytest.mark.django_db
def test_post_creates_reaction() -> None:
    message = _make_message()
    alice = UserFactory(username="alice")
    client = _auth_client(alice)

    response = client.post(
        f"/api/chat/messages/{message.id}/reactions/", {"emoji": "👍"}, format="json"
    )

    assert response.status_code == 201
    assert MessageReaction.objects.filter(message=message, user=alice, emoji="👍").exists()


@pytest.mark.django_db
def test_post_same_reaction_twice_is_idempotent() -> None:
    message = _make_message()
    alice = UserFactory(username="alice")
    client = _auth_client(alice)

    first = client.post(
        f"/api/chat/messages/{message.id}/reactions/", {"emoji": "👍"}, format="json"
    )
    second = client.post(
        f"/api/chat/messages/{message.id}/reactions/", {"emoji": "👍"}, format="json"
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert MessageReaction.objects.filter(message=message).count() == 1


@pytest.mark.django_db
def test_post_different_emoji_same_user() -> None:
    message = _make_message()
    alice = UserFactory(username="alice")
    client = _auth_client(alice)

    client.post(f"/api/chat/messages/{message.id}/reactions/", {"emoji": "👍"}, format="json")
    client.post(f"/api/chat/messages/{message.id}/reactions/", {"emoji": "❤️"}, format="json")

    assert MessageReaction.objects.filter(message=message, user=alice).count() == 2


@pytest.mark.django_db
def test_post_requires_auth() -> None:
    message = _make_message()

    response = APIClient().post(
        f"/api/chat/messages/{message.id}/reactions/", {"emoji": "👍"}, format="json"
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_post_404_when_message_missing() -> None:
    alice = UserFactory(username="alice")
    client = _auth_client(alice)

    response = client.post("/api/chat/messages/9999/reactions/", {"emoji": "👍"}, format="json")

    assert response.status_code == 404


@pytest.mark.django_db
def test_post_rejects_whitespace_emoji() -> None:
    message = _make_message()
    alice = UserFactory(username="alice")
    client = _auth_client(alice)

    response = client.post(
        f"/api/chat/messages/{message.id}/reactions/", {"emoji": " "}, format="json"
    )

    assert response.status_code == 400


# ==============================================================================
# DELETE /api/chat/messages/<pk>/reactions/<emoji>/
# ==============================================================================


@pytest.mark.django_db
def test_delete_removes_reaction() -> None:
    message = _make_message()
    alice = UserFactory(username="alice")
    MessageReaction.objects.create(message=message, user=alice, emoji="👍")
    client = _auth_client(alice)

    response = client.delete(f"/api/chat/messages/{message.id}/reactions/👍/")

    assert response.status_code == 204
    assert not MessageReaction.objects.filter(message=message, user=alice).exists()


@pytest.mark.django_db
def test_delete_nonexistent_is_idempotent() -> None:
    message = _make_message()
    alice = UserFactory(username="alice")
    client = _auth_client(alice)

    response = client.delete(f"/api/chat/messages/{message.id}/reactions/👍/")

    assert response.status_code == 204


@pytest.mark.django_db
def test_delete_only_affects_own_reaction() -> None:
    message = _make_message()
    alice = UserFactory(username="alice")
    bob = UserFactory(username="bob")
    MessageReaction.objects.create(message=message, user=alice, emoji="👍")
    MessageReaction.objects.create(message=message, user=bob, emoji="👍")
    client = _auth_client(alice)

    response = client.delete(f"/api/chat/messages/{message.id}/reactions/👍/")

    assert response.status_code == 204
    # Bob's reaction survives.
    assert MessageReaction.objects.filter(message=message, user=bob, emoji="👍").exists()
    assert not MessageReaction.objects.filter(message=message, user=alice).exists()


# ==============================================================================
# GET /api/chat/rooms/<name>/messages/ — reactions aggregation
# ==============================================================================


@pytest.mark.django_db
def test_message_list_includes_aggregated_reactions() -> None:
    message = _make_message()
    alice = UserFactory(username="alice")
    bob = UserFactory(username="bob")
    MessageReaction.objects.create(message=message, user=alice, emoji="👍")
    MessageReaction.objects.create(message=message, user=bob, emoji="👍")
    MessageReaction.objects.create(message=message, user=alice, emoji="❤️")
    client = _auth_client(alice)

    response = client.get("/api/chat/rooms/general/messages/")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    reactions = {r["emoji"]: r for r in payload[0]["reactions"]}
    assert reactions["👍"]["count"] == 2
    assert reactions["👍"]["me"] is True
    assert reactions["❤️"]["count"] == 1
    assert reactions["❤️"]["me"] is True


@pytest.mark.django_db
def test_me_flag_flips_per_viewer() -> None:
    message = _make_message()
    alice = UserFactory(username="alice")
    bob = UserFactory(username="bob")
    MessageReaction.objects.create(message=message, user=alice, emoji="👍")

    alice_view = _auth_client(alice).get("/api/chat/rooms/general/messages/").json()
    bob_view = _auth_client(bob).get("/api/chat/rooms/general/messages/").json()

    assert alice_view[0]["reactions"][0]["me"] is True
    assert bob_view[0]["reactions"][0]["me"] is False
