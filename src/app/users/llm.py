from django.conf import settings
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from .models import User

SYSTEM_PROMPT = """Ты — мистический рассказчик, который описывает людей через призму Таро.
Тебе дают карточку профиля пользователя в стилистике арканов и стихий.
Ты пишешь короткое (200-300 слов) психологическое описание этого человека:
- его сильные стороны и тени;
- внутренний конфликт, если он есть;
- как окружение друзей влияет на его динамику;
- что его ждёт впереди.
Отвечай только на русском, метафорически, в литературном стиле.
Не используй маркированные списки, пиши сплошным текстом в 2-3 абзаца."""

USER_PROMPT_TEMPLATE = """Профиль:
- Имя: {username}
- Возраст: {age}
- Локация: {location}
- Аркана: {arcana}
- Стихия: {element}
- Тень: {shadow}
- Путь: {quest}
- Проклятие: {curse}
- Тотем: {totem}
- Запретная магия: {forbidden_magic}

Арканы друзей: {friends_arcanas}

Опиши этого человека."""


def _build_messages(user: User) -> list:
    profile = user.profile
    friends_arcanas = [
        f.friend.profile.get_arcana_display()
        for f in user.friendships_initiated.select_related("friend__profile").all()
        if f.friend.profile.arcana
    ]
    template = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("human", USER_PROMPT_TEMPLATE)]
    )
    return template.format_messages(
        username=user.username,
        age=profile.age or "не указан",
        location=profile.location or "не указана",
        arcana=profile.get_arcana_display() or "не выбрана",
        element=profile.get_element_display() or "не выбрана",
        shadow=profile.shadow or "не описана",
        quest=profile.quest or "не описан",
        curse=profile.curse or "не описано",
        totem=profile.totem or "не описан",
        forbidden_magic=profile.forbidden_magic or "не описана",
        friends_arcanas=", ".join(friends_arcanas) if friends_arcanas else "нет друзей",
    )


def build_portrait_prompt(user: User) -> str:
    """Render the prompt as a single string. Used for tests + debugging."""
    return "\n\n".join(msg.content for msg in _build_messages(user))


def generate_portrait(user: User) -> str:
    """Call Ollama and return the generated portrait text."""
    llm = ChatOllama(
        base_url=settings.OLLAMA_URL,
        model=settings.OLLAMA_MODEL,
        temperature=0.8,
    )
    response = llm.invoke(_build_messages(user))
    return str(response.content)
