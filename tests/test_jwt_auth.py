import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from tests.factories import UserFactory

User = get_user_model()


# ==============================================================================
# Register
# ==============================================================================


@pytest.mark.django_db
def test_register_creates_user(client: Client) -> None:
    response = client.post(
        "/api/auth/register/",
        data={"username": "alice", "email": "alice@example.com", "password": "pass1234"},
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"
    assert "password" not in body
    assert User.objects.filter(username="alice").exists()


@pytest.mark.django_db
def test_register_rejects_duplicate_username(client: Client) -> None:
    UserFactory(username="alice")

    response = client.post(
        "/api/auth/register/",
        data={"username": "alice", "email": "other@example.com", "password": "pass1234"},
        content_type="application/json",
    )

    assert response.status_code == 400


# ==============================================================================
# Login
# ==============================================================================


@pytest.mark.django_db
def test_login_returns_access_and_refresh(client: Client) -> None:
    UserFactory(username="alice")

    response = client.post(
        "/api/auth/login/",
        data={"username": "alice", "password": "password123"},
        content_type="application/json",
    )

    assert response.status_code == 200
    body = response.json()
    assert "access" in body
    assert "refresh" in body


@pytest.mark.django_db
def test_login_rejects_wrong_password(client: Client) -> None:
    UserFactory(username="alice")

    response = client.post(
        "/api/auth/login/",
        data={"username": "alice", "password": "wrong"},
        content_type="application/json",
    )

    assert response.status_code == 401


# ==============================================================================
# Me
# ==============================================================================


@pytest.mark.django_db
def test_me_returns_current_user(client: Client) -> None:
    UserFactory(username="alice", email="alice@example.com")
    tokens = client.post(
        "/api/auth/login/",
        data={"username": "alice", "password": "password123"},
        content_type="application/json",
    ).json()

    response = client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"


@pytest.mark.django_db
def test_me_requires_token(client: Client) -> None:
    response = client.get("/api/auth/me/")

    assert response.status_code == 401


# ==============================================================================
# Refresh
# ==============================================================================


@pytest.mark.django_db
def test_refresh_issues_new_access(client: Client) -> None:
    UserFactory(username="alice")
    tokens = client.post(
        "/api/auth/login/",
        data={"username": "alice", "password": "password123"},
        content_type="application/json",
    ).json()

    response = client.post(
        "/api/auth/refresh/",
        data={"refresh": tokens["refresh"]},
        content_type="application/json",
    )

    assert response.status_code == 200
    body = response.json()
    assert "access" in body


# ==============================================================================
# Logout (blacklist)
# ==============================================================================


@pytest.mark.django_db
def test_logout_blacklists_refresh_token(client: Client) -> None:
    UserFactory(username="alice")
    tokens = client.post(
        "/api/auth/login/",
        data={"username": "alice", "password": "password123"},
        content_type="application/json",
    ).json()

    logout = client.post(
        "/api/auth/logout/",
        data={"refresh": tokens["refresh"]},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
    )

    assert logout.status_code == 205

    reuse = client.post(
        "/api/auth/refresh/",
        data={"refresh": tokens["refresh"]},
        content_type="application/json",
    )

    assert reuse.status_code == 401


@pytest.mark.django_db
def test_logout_requires_authentication(client: Client) -> None:
    response = client.post(
        "/api/auth/logout/",
        data={"refresh": "irrelevant"},
        content_type="application/json",
    )

    assert response.status_code == 401
