import pytest

from tests.factories import UserFactory


def test_landing_renders_for_anonymous(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Войти" in response.content.decode()


@pytest.mark.django_db
def test_landing_redirects_authenticated_to_portrait(client):
    client.force_login(UserFactory())
    response = client.get("/")
    assert response.status_code == 302
    assert response["Location"] == "/portrait/"
