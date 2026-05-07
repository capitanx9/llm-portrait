"""Cross-cutting HTTP middleware (logging, request-id propagation)."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from loguru import logger


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
