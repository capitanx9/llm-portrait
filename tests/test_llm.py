from unittest.mock import patch

import pytest

from app.users.llm import build_portrait_prompt, generate_portrait
from app.users.models import UserFriends, UserProfile
from tests.factories import UserFactory

# ==============================================================================
# Prompt building
# ==============================================================================


@pytest.mark.django_db
def test_build_portrait_prompt_includes_all_fields():
    user = UserFactory(username="alice")
    profile = UserProfile.objects.get(user=user)
    profile.age = 30
    profile.location = "Харьков"
    profile.arcana = "magician"
    profile.element = "fire"
    profile.shadow = "Прячу перфекционизм."
    profile.quest = "Найти баланс."
    profile.curse = "Откладываю важное."
    profile.totem = "Сова."
    profile.forbidden_magic = "Чтение мыслей."
    profile.save()

    friend = UserFactory(username="bob")
    friend_profile = UserProfile.objects.get(user=friend)
    friend_profile.arcana = "priestess"
    friend_profile.save()
    UserFriends.objects.create(user=user, friend=friend)

    user.refresh_from_db()
    prompt = build_portrait_prompt(user)

    assert "alice" in prompt
    assert "30" in prompt
    assert "Харьков" in prompt
    assert "Маг" in prompt
    assert "Огонь" in prompt
    assert "перфекционизм" in prompt
    assert "Жрица" in prompt


@pytest.mark.django_db
def test_build_portrait_prompt_with_empty_profile():
    user = UserFactory(username="alice")

    prompt = build_portrait_prompt(user)

    assert "alice" in prompt
    assert "не указан" in prompt
    assert "не выбрана" in prompt
    assert "нет друзей" in prompt


# ==============================================================================
# Ollama call
# ==============================================================================


@pytest.mark.django_db
def test_generate_portrait_calls_ollama():
    user = UserFactory(username="alice")

    with patch("app.users.llm.ChatOllama") as mock_ollama:
        mock_ollama.return_value.invoke.return_value.content = "Mocked portrait."
        result = generate_portrait(user)

    assert result == "Mocked portrait."
    mock_ollama.assert_called_once()
    mock_ollama.return_value.invoke.assert_called_once()
