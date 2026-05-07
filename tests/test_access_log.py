"""Tests for HttpAccessLogMiddleware and the redaction helpers."""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from django.test import Client
from loguru import logger

from app.core.log_redact import redact_body, redact_headers


@pytest.fixture
def loguru_records() -> Iterator[list[dict]]:
    """Capture every loguru record emitted during the test as a list of dicts.

    pytest's built-in `caplog` watches stdlib logging only; our access log
    is written through loguru (which feeds *into* stdlib at the root, but
    caplog won't see records produced after pytest's handler is detached).
    Adding our own sink keeps the assertion target small and explicit.
    """
    captured: list[dict] = []

    def sink(message) -> None:  # type: ignore[no-untyped-def]
        record = message.record
        captured.append(
            {
                "level": record["level"].name,
                "message": record["message"],
                "extra": dict(record["extra"]),
            }
        )

    handler_id = logger.add(sink, level="DEBUG")
    try:
        yield captured
    finally:
        logger.remove(handler_id)


def _access_record(records: list[dict], path: str) -> dict | None:
    """Find the access-log record for `path` in the captured stream."""
    for rec in records:
        extra = rec["extra"]
        if extra.get("path") == path and "method" in extra:
            return rec
    return None


# ==============================================================================
# Metadata (always logged)
# ==============================================================================


def test_access_log_records_basic_metadata(client: Client, loguru_records: list[dict]) -> None:
    response = client.get("/health/")

    assert response.status_code == 200
    record = _access_record(loguru_records, "/health/")
    assert record is not None
    assert record["level"] == "INFO"
    assert record["extra"]["method"] == "GET"
    assert record["extra"]["status"] == 200
    assert record["extra"]["user_id"] == "anon"
    assert "duration_ms" in record["extra"]
    assert record["extra"]["view_name"] == "core:health"


@pytest.mark.django_db
def test_access_log_warning_for_4xx(client: Client, loguru_records: list[dict]) -> None:
    response = client.post(
        "/api/auth/login/",
        data={"username": "ghost", "password": "wrongpass"},
        content_type="application/json",
    )

    assert response.status_code == 401
    record = _access_record(loguru_records, "/api/auth/login/")
    assert record is not None
    assert record["level"] == "WARNING"


# ==============================================================================
# Body dump (LOG_HTTP_BODY=1)
# ==============================================================================


@pytest.mark.django_db
def test_body_dump_off_by_default(
    loguru_records: list[dict], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Force the off-state explicitly so the test doesn't rely on whatever
    # the developer happens to have in their .env.
    monkeypatch.delenv("LOG_HTTP_BODY", raising=False)
    fresh = Client()

    fresh.post(
        "/api/auth/register/",
        data={"username": "alice", "email": "a@example.com", "password": "pass1234"},
        content_type="application/json",
    )
    record = _access_record(loguru_records, "/api/auth/register/")
    assert record is not None
    assert "request_body" not in record["extra"]
    assert "request_headers" not in record["extra"]


@pytest.mark.django_db
def test_body_dump_on_redacts_password(
    client: Client, loguru_records: list[dict], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LOG_HTTP_BODY", "1")
    # The middleware reads the env var at construction; rebuild the client
    # so it picks up the new value through a fresh middleware instance.
    fresh = Client()

    fresh.post(
        "/api/auth/register/",
        data={"username": "alice", "email": "a@example.com", "password": "pass1234"},
        content_type="application/json",
    )
    record = _access_record(loguru_records, "/api/auth/register/")
    assert record is not None
    body = record["extra"]["request_body"]
    assert isinstance(body, dict)
    assert body["password"] == "***"
    assert body["username"] == "alice"  # non-sensitive field passes through


@pytest.mark.django_db
def test_body_dump_redacts_authorization_header(
    client: Client, loguru_records: list[dict], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LOG_HTTP_BODY", "1")
    fresh = Client()

    fresh.get("/health/", HTTP_AUTHORIZATION="Bearer super-secret-token")

    record = _access_record(loguru_records, "/health/")
    assert record is not None
    headers = record["extra"]["request_headers"]
    assert headers["Authorization"] == "***"


def test_body_dump_truncates_large_payload(
    client: Client, loguru_records: list[dict], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LOG_HTTP_BODY", "1")
    fresh = Client()

    huge = {"items": ["x" * 100 for _ in range(200)]}  # > 4 KB serialised
    fresh.post(
        "/api/chat/rooms/",
        data=json.dumps(huge),
        content_type="application/json",
    )
    record = _access_record(loguru_records, "/api/chat/rooms/")
    assert record is not None
    body = record["extra"]["request_body"]
    # Truncated payloads come back as "<invalid json, N bytes>" because the
    # tail of the cut-off JSON is unparseable. The exact shape doesn't
    # matter as long as we didn't dump the full 20 KB into the log.
    assert isinstance(body, str) and "bytes" in body


# ==============================================================================
# Redaction helpers (unit)
# ==============================================================================


def test_redact_body_walks_nested_structures() -> None:
    payload = {
        "user": {"email": "a@b.com", "password": "p"},
        "creds": [{"access_token": "x"}, {"refresh_token": "y"}],
        "note": "ok",
    }
    redacted = redact_body(payload)

    assert redacted["user"]["password"] == "***"
    assert redacted["user"]["email"] == "a@b.com"
    assert redacted["creds"][0]["access_token"] == "***"
    assert redacted["creds"][1]["refresh_token"] == "***"
    assert redacted["note"] == "ok"


def test_redact_body_masks_whole_subtree_when_key_is_sensitive() -> None:
    # `tokens` itself contains "token" → we mask the whole value, not just
    # leaves underneath. That's the safer default: if the field name says
    # secret, don't peek inside hoping the children are fine.
    payload = {"tokens": [{"name": "ssh"}, {"name": "api"}]}

    assert redact_body(payload) == {"tokens": "***"}


def test_redact_headers_is_case_insensitive() -> None:
    headers = {"authorization": "Bearer x", "X-Custom": "keep"}
    out = redact_headers(headers)

    assert out["authorization"] == "***"
    assert out["X-Custom"] == "keep"
