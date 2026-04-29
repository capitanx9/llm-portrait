from unittest.mock import patch

import pytest
from django.core.cache import cache

from app.users.models import UserProfile
from tests.factories import UserFactory


@pytest.fixture(autouse=True)
def clear_ratelimit_cache():
    cache.clear()
    yield
    cache.clear()


# ==============================================================================
# Auth
# ==============================================================================


def test_generate_anon_redirects_to_login(client):
    response = client.post("/portrait/generate/")
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


# ==============================================================================
# Happy path
# ==============================================================================


@pytest.mark.django_db
def test_generate_invokes_llm_and_saves_description(client):
    user = UserFactory()
    client.force_login(user)

    with patch("app.users.views.generate_portrait", return_value="test description"):
        response = client.post("/portrait/generate/")

    assert response.status_code == 302
    profile = UserProfile.objects.get(user=user)
    assert profile.description == "test description"


# ==============================================================================
# Error handling
# ==============================================================================


@pytest.mark.django_db
def test_generate_handles_llm_error(client):
    user = UserFactory()
    client.force_login(user)

    with patch("app.users.views.generate_portrait", side_effect=Exception("ollama down")):
        response = client.post("/portrait/generate/")

    assert response.status_code == 302
    profile = UserProfile.objects.get(user=user)
    assert profile.description == ""


# ==============================================================================
# Rate limit
# ==============================================================================


@pytest.mark.django_db
def test_generate_rate_limit_after_3_calls(client, settings):
    settings.LLM_RATE_LIMIT = "3/h"
    user = UserFactory()
    client.force_login(user)

    with patch("app.users.views.generate_portrait", return_value="ok"):
        for _ in range(3):
            response = client.post("/portrait/generate/")
            assert response.status_code == 302

        response = client.post("/portrait/generate/")
        assert response.status_code == 302

    profile = UserProfile.objects.get(user=user)
    assert profile.description == "ok"
