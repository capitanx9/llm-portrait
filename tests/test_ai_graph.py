from unittest.mock import MagicMock, patch

import pytest
from django.test import Client

from app.ai import nodes
from app.ai.graph import build_graph
from app.ai.nodes import (
    _safe,
    condition_router,
    detect_lang_node,
    summarize_node,
    translate_node,
)
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


def _llm_returning(content: str) -> MagicMock:
    fake = MagicMock()
    fake.invoke.return_value.content = content
    return fake


# ==============================================================================
# detect_lang_node
# ==============================================================================


def test_detect_lang_node_returns_two_letter_code() -> None:
    with patch.object(nodes, "_make_llm", return_value=_llm_returning("en")):
        result = detect_lang_node({"action": "translate", "message": "Hello"})
    assert result == {"source_language": "en"}


def test_detect_lang_node_normalises_noisy_response() -> None:
    with patch.object(nodes, "_make_llm", return_value=_llm_returning("  EN.  ")):
        result = detect_lang_node({"action": "translate", "message": "Hello"})
    assert result == {"source_language": "en"}


def test_detect_lang_node_falls_back_to_en_for_unknown_code() -> None:
    with patch.object(nodes, "_make_llm", return_value=_llm_returning("zz")):
        result = detect_lang_node({"action": "translate", "message": "Hello"})
    assert result == {"source_language": "en"}


# ==============================================================================
# translate_node
# ==============================================================================


def test_translate_node_calls_llm_with_target_language() -> None:
    fake = _llm_returning("Bonjour")
    with patch.object(nodes, "_make_llm", return_value=fake):
        result = translate_node(
            {
                "action": "translate",
                "message": "Hello",
                "target_language": "fr",
            }
        )
    assert result == {"translation": "Bonjour"}
    sent_messages = fake.invoke.call_args.args[0]
    rendered = "\n".join(m.content for m in sent_messages)
    assert "fr" in rendered
    assert "Hello" in rendered


# ==============================================================================
# summarize_node
# ==============================================================================


def test_summarize_node_truncates_long_conversation() -> None:
    fake = _llm_returning("summary text")
    long_convo = [{"role": "user", "content": f"msg{i}"} for i in range(500)]
    with patch.object(nodes, "_make_llm", return_value=fake):
        summarize_node(
            {
                "action": "summarize",
                "conversation": long_convo,
                "source_language": "en",
            }
        )
    sent_messages = fake.invoke.call_args.args[0]
    rendered = "\n".join(m.content for m in sent_messages)
    # First-of-cap turn must appear; pre-cap turns must not.
    assert "msg460" in rendered
    assert "msg10" not in rendered


def test_summarize_node_returns_summary_string() -> None:
    fake = _llm_returning("Concise overview.")
    with patch.object(nodes, "_make_llm", return_value=fake):
        result = summarize_node(
            {
                "action": "summarize",
                "conversation": [{"role": "user", "content": "hi"}],
                "source_language": "en",
            }
        )
    assert result == {"summary": "Concise overview."}


# ==============================================================================
# condition_router
# ==============================================================================


def test_condition_router_picks_translate_branch() -> None:
    assert condition_router({"action": "translate"}) == "translate"


def test_condition_router_picks_summarize_branch() -> None:
    assert condition_router({"action": "summarize"}) == "summarize"


def test_condition_router_routes_to_fallback_on_error_in_state() -> None:
    assert condition_router({"action": "translate", "error": "boom"}) == "fallback"


# ==============================================================================
# _safe decorator
# ==============================================================================


def test_safe_decorator_captures_exception_into_state() -> None:
    def boom_node(state: dict) -> dict:
        raise ValueError("kaboom")

    wrapped = _safe(boom_node)
    result = wrapped({"action": "translate"})
    assert result == {"error": "kaboom", "failed_node": "boom"}


# ==============================================================================
# Compiled graph (end-to-end through StateGraph)
# ==============================================================================


def test_graph_translate_end_to_end() -> None:
    fake_detect = _llm_returning("ru")
    fake_translate = _llm_returning("Hello, world!")
    with patch.object(nodes, "_make_llm", side_effect=[fake_detect, fake_translate]):
        graph = build_graph()
        final = graph.invoke(
            {
                "action": "translate",
                "message": "Привет, мир!",
                "target_language": "en",
            }
        )
    assert final["source_language"] == "ru"
    assert final["translation"] == "Hello, world!"
    assert "error" not in final


def test_graph_summarize_end_to_end() -> None:
    fake_detect = _llm_returning("en")
    fake_sum = _llm_returning("Two friends greet each other.")
    with patch.object(nodes, "_make_llm", side_effect=[fake_detect, fake_sum]):
        graph = build_graph()
        final = graph.invoke(
            {
                "action": "summarize",
                "conversation": [
                    {"role": "user", "content": "Hi"},
                    {"role": "assistant", "content": "Hello!"},
                ],
            }
        )
    assert final["source_language"] == "en"
    assert final["summary"] == "Two friends greet each other."
    assert "error" not in final


def test_graph_falls_back_when_translate_node_raises() -> None:
    fake_detect = _llm_returning("en")
    failing = MagicMock()
    failing.invoke.side_effect = RuntimeError("upstream down")
    with patch.object(nodes, "_make_llm", side_effect=[fake_detect, failing]):
        graph = build_graph()
        final = graph.invoke(
            {
                "action": "translate",
                "message": "Hello",
                "target_language": "fr",
            }
        )
    assert final["error"] == "upstream down"
    assert final["failed_node"] == "translate"
    assert "translation" not in final


# ==============================================================================
# AIProcessView (HTTP layer)
# ==============================================================================


@pytest.mark.django_db
def test_view_requires_authentication(client: Client) -> None:
    response = client.post(
        "/api/ai/process/",
        data={"action": "translate", "message": "Hi", "target_language": "fr"},
        content_type="application/json",
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_view_rejects_translate_without_target_language(client: Client) -> None:
    headers = _auth_header(client)
    response = client.post(
        "/api/ai/process/",
        data={"action": "translate", "message": "Hi"},
        content_type="application/json",
        **headers,
    )
    assert response.status_code == 400
    assert "target_language" in response.json()


@pytest.mark.django_db
def test_view_rejects_summarize_without_conversation(client: Client) -> None:
    headers = _auth_header(client)
    response = client.post(
        "/api/ai/process/",
        data={"action": "summarize"},
        content_type="application/json",
        **headers,
    )
    assert response.status_code == 400
    assert "conversation" in response.json()


@pytest.mark.django_db
def test_view_rejects_unknown_action(client: Client) -> None:
    headers = _auth_header(client)
    response = client.post(
        "/api/ai/process/",
        data={"action": "transmogrify"},
        content_type="application/json",
        **headers,
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_view_translate_returns_200_with_payload(client: Client) -> None:
    headers = _auth_header(client)
    fake_result = {"source_language": "ru", "translation": "Hello"}
    with patch("app.ai.views.run_graph", return_value=fake_result):
        response = client.post(
            "/api/ai/process/",
            data={"action": "translate", "message": "Привет", "target_language": "en"},
            content_type="application/json",
            **headers,
        )
    assert response.status_code == 200
    assert response.json() == {
        "action": "translate",
        "source_language": "ru",
        "translation": "Hello",
    }


@pytest.mark.django_db
def test_view_summarize_returns_200_with_payload(client: Client) -> None:
    headers = _auth_header(client)
    fake_result = {"source_language": "en", "summary": "Brief overview."}
    with patch("app.ai.views.run_graph", return_value=fake_result):
        response = client.post(
            "/api/ai/process/",
            data={
                "action": "summarize",
                "conversation": [{"role": "user", "content": "Hi"}],
            },
            content_type="application/json",
            **headers,
        )
    assert response.status_code == 200
    assert response.json() == {
        "action": "summarize",
        "source_language": "en",
        "summary": "Brief overview.",
    }


@pytest.mark.django_db
def test_view_returns_503_when_graph_returns_error(client: Client) -> None:
    headers = _auth_header(client)
    with patch(
        "app.ai.views.run_graph",
        return_value={"error": "boom", "failed_node": "translate"},
    ):
        response = client.post(
            "/api/ai/process/",
            data={"action": "translate", "message": "Hi", "target_language": "fr"},
            content_type="application/json",
            **headers,
        )
    assert response.status_code == 503
    assert response.json() == {"detail": "boom"}


@pytest.mark.django_db
def test_view_ratelimit_returns_429_after_threshold(
    client: Client, settings: pytest.FixtureRequest
) -> None:
    # Force a tiny ratelimit just for this test so two requests trip it
    # without hammering the LLM mock more than necessary.
    settings.LLM_RATE_LIMIT = "2/m"  # type: ignore[attr-defined]
    headers = _auth_header(client)
    payload = {"action": "translate", "message": "Hi", "target_language": "fr"}

    with patch(
        "app.ai.views.run_graph",
        return_value={"source_language": "en", "translation": "Salut"},
    ):
        first = client.post(
            "/api/ai/process/", data=payload, content_type="application/json", **headers
        )
        second = client.post(
            "/api/ai/process/", data=payload, content_type="application/json", **headers
        )
        third = client.post(
            "/api/ai/process/", data=payload, content_type="application/json", **headers
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json() == {"detail": "Too many requests."}
