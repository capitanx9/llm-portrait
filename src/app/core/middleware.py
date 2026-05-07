"""Cross-cutting HTTP middleware (logging, request-id propagation)."""

from __future__ import annotations

import json
import os
import time
import uuid
from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, HttpResponse
from loguru import logger

from app.core.log_redact import redact_body, redact_headers

_BODY_BYTE_LIMIT = 4096
_TRUNCATED_MARKER = "...[truncated]"


class RequestIdMiddleware:
    """Generate (or take from header) a request id and bind it to loguru.

    Every log line emitted while the request runs gets `request_id=...`
    attached, so a single greppable token connects the entry log, every
    SQL query, signal, downstream Celery task and outgoing email. The id
    is also echoed back as the `X-Request-ID` response header so a
    frontend or external caller can quote it when reporting a bug.
    """

    HEADER = "X-Request-ID"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        incoming = request.headers.get(self.HEADER)
        request_id = incoming or uuid.uuid4().hex[:12]
        request.id = request_id  # type: ignore[attr-defined]

        with logger.contextualize(request_id=request_id):
            response = self.get_response(request)

        response[self.HEADER] = request_id
        return response


class HttpAccessLogMiddleware:
    """One structured log line per HTTP request.

    Always logs metadata (method, path, status, duration, user, view, ip).
    When `LOG_HTTP_BODY=1` is set, additionally dumps headers and JSON
    bodies — redacted (passwords, tokens) and truncated (4 KB). The flag
    is meant for local debugging only: we never want raw request bodies
    in a production log stream.

    Severity follows the response status: 2xx/3xx → INFO, 4xx → WARNING,
    5xx → ERROR. That keeps casual log filtering useful (`level>=warning`
    surfaces every failed request) without introducing a new logger name.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.dump_body = os.environ.get("LOG_HTTP_BODY") == "1"

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Read the body up front: Django caches it on `request._body` so
        # DRF / form parsers downstream can still see it. If we waited until
        # after `get_response`, the underlying stream might already be
        # consumed and `request.body` would raise.
        request_body = request.body if self.dump_body else b""

        started = time.perf_counter()
        response = self.get_response(request)
        duration_ms = (time.perf_counter() - started) * 1000

        bound: dict[str, Any] = {
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "user_id": _user_id(request),
            "client_ip": _client_ip(request),
            "view_name": _view_name(request),
        }

        message = (
            f"{request.method} {request.path} "
            f"{response.status_code} in {bound['duration_ms']}ms"
        )
        if self.dump_body:
            bound["request_headers"] = redact_headers(dict(request.headers))
            bound["request_body"] = _decode_body(request_body, request.content_type or "")
            bound["response_headers"] = redact_headers(dict(response.items()))
            bound["response_body"] = _decode_response_body(response)
            # Append a compact JSON dump to the message itself so the body
            # shows up in the human-readable log format too (loguru's format
            # string can't render arbitrary `extra` keys without listing
            # them up front). In LOG_FORMAT=json the same data is emitted
            # structurally via `serialize=True` and the extra fields above.
            message = f"{message} | {json.dumps({k: bound[k] for k in _DUMP_KEYS}, default=str)}"

        logger.bind(**bound).log(_level_for(response.status_code), message)
        return response


_DUMP_KEYS = ("request_headers", "request_body", "response_headers", "response_body")


def _user_id(request: HttpRequest) -> int | str:
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return "anon"
    return getattr(user, "pk", "anon")


def _client_ip(request: HttpRequest) -> str:
    # X-Forwarded-For is set by nginx in prod. The first value is the
    # original client; the rest are proxies. In dev there's no proxy and
    # we fall back to REMOTE_ADDR.
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _view_name(request: HttpRequest) -> str:
    match = getattr(request, "resolver_match", None)
    if match is None:
        return ""
    return match.view_name or ""


def _level_for(status: int) -> str:
    if status >= 500:
        return "ERROR"
    if status >= 400:
        return "WARNING"
    return "INFO"


def _decode_body(raw: bytes, content_type: str) -> Any:
    """Decode a request body for logging.

    JSON bodies are parsed and returned as a redacted dict/list so they
    show up structurally in `LOG_FORMAT=json`. Non-JSON bodies (form-data,
    multipart, binary) are reported as a one-line summary instead of
    being dumped — multipart can be megabytes and form-urlencoded fields
    of interest end up in `request.POST`, which DRF echoes anyway.
    """
    if not raw:
        return ""
    truncated = len(raw) > _BODY_BYTE_LIMIT
    payload = raw[:_BODY_BYTE_LIMIT]

    if content_type.startswith("application/json"):
        try:
            decoded = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return f"<invalid json, {len(raw)} bytes>"
        return redact_body(decoded)

    suffix = _TRUNCATED_MARKER if truncated else ""
    return f"<{content_type or 'unknown'}, {len(raw)} bytes{suffix}>"


def _decode_response_body(response: HttpResponse) -> Any:
    content_type = response.get("Content-Type", "")
    if not content_type.startswith("application/json"):
        return f"<{content_type or 'unknown'}>"
    if getattr(response, "streaming", False):
        return "<streaming>"

    raw = response.content
    truncated = len(raw) > _BODY_BYTE_LIMIT
    payload = raw[:_BODY_BYTE_LIMIT]
    try:
        decoded = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return f"<invalid json, {len(raw)} bytes>"

    redacted = redact_body(decoded)
    if truncated:
        return {"_truncated": True, "_size": len(raw), "preview": redacted}
    return redacted
