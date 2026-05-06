import pytest
from django.test import Client

from app.chat.models import Message, Room
from tests.factories import UserFactory


def _auth_header(client: Client, username: str = "alice") -> dict[str, str]:
    UserFactory(username=username)
    response = client.post(
        "/api/auth/login/",
        data={"username": username, "password": "password123"},
        content_type="application/json",
    )
    access = response.json()["access"]
    return {"HTTP_AUTHORIZATION": f"Bearer {access}"}


# ==============================================================================
# Auth gating
# ==============================================================================


@pytest.mark.django_db
def test_rooms_list_requires_authentication(client: Client) -> None:
    assert client.get("/api/chat/rooms/").status_code == 401


@pytest.mark.django_db
def test_room_messages_requires_authentication(client: Client) -> None:
    Room.objects.create(name="general")
    assert client.get("/api/chat/rooms/general/messages/").status_code == 401


# ==============================================================================
# Rooms list / create
# ==============================================================================


@pytest.mark.django_db
def test_rooms_list_returns_existing_rooms(client: Client) -> None:
    headers = _auth_header(client)
    Room.objects.create(name="general")
    Room.objects.create(name="random")

    response = client.get("/api/chat/rooms/", **headers)

    assert response.status_code == 200
    names = {r["name"] for r in response.json()["results"]}
    assert names == {"general", "random"}


@pytest.mark.django_db
def test_rooms_create_returns_201_for_new_room(client: Client) -> None:
    headers = _auth_header(client)
    response = client.post(
        "/api/chat/rooms/",
        data={"name": "general"},
        content_type="application/json",
        **headers,
    )
    assert response.status_code == 201
    assert response.json()["name"] == "general"


@pytest.mark.django_db
def test_rooms_create_is_idempotent(client: Client) -> None:
    headers = _auth_header(client)
    Room.objects.create(name="general")

    response = client.post(
        "/api/chat/rooms/",
        data={"name": "general"},
        content_type="application/json",
        **headers,
    )

    assert response.status_code == 200
    assert Room.objects.filter(name="general").count() == 1


@pytest.mark.django_db
def test_rooms_create_rejects_invalid_name(client: Client) -> None:
    headers = _auth_header(client)
    response = client.post(
        "/api/chat/rooms/",
        data={"name": "Bad Name!"},
        content_type="application/json",
        **headers,
    )
    assert response.status_code == 400


# ==============================================================================
# Messages history
# ==============================================================================


@pytest.mark.django_db
def test_messages_history_returns_newest_first(client: Client) -> None:
    headers = _auth_header(client)
    user = UserFactory(username="bob")
    room = Room.objects.create(name="general")
    Message.objects.create(room=room, sender=user, text="one")
    Message.objects.create(room=room, sender=user, text="two")

    response = client.get("/api/chat/rooms/general/messages/", **headers)

    assert response.status_code == 200
    body = response.json()
    assert [m["text"] for m in body] == ["two", "one"]


@pytest.mark.django_db
def test_messages_history_respects_before_cursor(client: Client) -> None:
    headers = _auth_header(client)
    user = UserFactory(username="bob")
    room = Room.objects.create(name="general")
    m1 = Message.objects.create(room=room, sender=user, text="one")
    m2 = Message.objects.create(room=room, sender=user, text="two")
    Message.objects.create(room=room, sender=user, text="three")

    response = client.get(
        f"/api/chat/rooms/general/messages/?before={m2.id}",
        **headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert [m["id"] for m in body] == [m1.id]


@pytest.mark.django_db
def test_messages_history_returns_404_for_missing_room(client: Client) -> None:
    headers = _auth_header(client)
    response = client.get("/api/chat/rooms/nonexistent/messages/", **headers)
    assert response.status_code == 404
