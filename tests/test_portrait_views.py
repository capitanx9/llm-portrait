import pytest

from app.users.models import UserProfile
from tests.factories import UserFactory


def test_portrait_anon_redirects_to_login(client):
    response = client.get("/portrait/")
    assert response.status_code == 302
    assert response["Location"] == "/accounts/login/?next=/portrait/"


@pytest.mark.django_db
def test_portrait_renders_for_authenticated_user(client):
    client.force_login(UserFactory())
    response = client.get("/portrait/")
    assert response.status_code == 200
    content = response.content.decode()
    assert "Мой портрет" in content
    assert "Все пользователи" in content


@pytest.mark.django_db
def test_portrait_save_updates_profile(client):
    user = UserFactory()
    client.force_login(user)
    response = client.post(
        "/portrait/",
        {
            "age": 30,
            "location": "Берлин",
            "arcana": "magician",
            "element": "fire",
            "shadow": "Длинная фраза тени",
            "quest": "Длинная фраза пути",
            "curse": "Длинная фраза проклятия",
            "totem": "",
            "forbidden_magic": "",
        },
    )
    assert response.status_code == 302
    profile = UserProfile.objects.get(user=user)
    assert profile.age == 30
    assert profile.location == "Берлин"
    assert profile.arcana == "magician"


@pytest.mark.django_db
def test_portrait_save_with_invalid_age(client):
    user = UserFactory()
    client.force_login(user)
    response = client.post(
        "/portrait/",
        {
            "age": 200,
            "location": "",
            "arcana": "",
            "element": "",
            "shadow": "",
            "quest": "",
            "curse": "",
            "totem": "",
            "forbidden_magic": "",
        },
    )
    assert response.status_code == 200
    profile = UserProfile.objects.get(user=user)
    assert profile.age != 200
