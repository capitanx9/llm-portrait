import pytest

from app.users.models import User, UserProfile
from tests.factories import UserFactory

# ==============================================================================
# Login page rendering
# ==============================================================================


@pytest.mark.django_db
def test_login_page_shows_github_button(client):
    response = client.get("/accounts/login/")
    assert response.status_code == 200
    assert "GitHub" in response.content.decode()


@pytest.mark.django_db
def test_login_page_shows_password_form(client):
    response = client.get("/accounts/login/")
    content = response.content.decode()
    assert 'name="login"' in content
    assert 'name="password"' in content


# ==============================================================================
# Password login
# ==============================================================================


@pytest.mark.django_db
def test_login_with_username_password_succeeds(client):
    UserFactory(username="alice")
    response = client.post(
        "/accounts/login/",
        {"login": "alice", "password": "password123"},
    )
    assert response.status_code == 302
    assert response["Location"] == "/portrait/"


@pytest.mark.django_db
def test_login_with_bad_password_fails(client):
    UserFactory(username="alice")
    response = client.post(
        "/accounts/login/",
        {"login": "alice", "password": "wrong"},
    )
    assert response.status_code == 200


# ==============================================================================
# Signup
# ==============================================================================


@pytest.mark.django_db
def test_signup_creates_user_and_profile(client):
    response = client.post(
        "/accounts/signup/",
        {
            "username": "newuser",
            "email": "newuser@example.com",
            "password1": "Strong-Pass-9482",
            "password2": "Strong-Pass-9482",
        },
    )
    assert response.status_code == 302
    user = User.objects.get(username="newuser")
    assert user.email == "newuser@example.com"
    assert UserProfile.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_signup_with_mismatched_passwords_fails(client):
    response = client.post(
        "/accounts/signup/",
        {
            "username": "newuser",
            "email": "newuser@example.com",
            "password1": "Strong-Pass-9482",
            "password2": "Different-Pass-1111",
        },
    )
    assert response.status_code == 200
    assert not User.objects.filter(username="newuser").exists()


@pytest.mark.django_db
def test_signup_with_existing_username_fails(client):
    UserFactory(username="alice")
    response = client.post(
        "/accounts/signup/",
        {
            "username": "alice",
            "email": "another@example.com",
            "password1": "Strong-Pass-9482",
            "password2": "Strong-Pass-9482",
        },
    )
    assert response.status_code == 200


# ==============================================================================
# Logout
# ==============================================================================


@pytest.mark.django_db
def test_logout_returns_to_landing(client):
    client.force_login(UserFactory())
    response = client.post("/accounts/logout/")
    assert response.status_code == 302
    assert response["Location"] == "/"


# ==============================================================================
# Password reset
# ==============================================================================


@pytest.mark.django_db
def test_password_reset_request_renders(client):
    response = client.get("/accounts/password/reset/")
    assert response.status_code == 200
    assert "Email" in response.content.decode()
