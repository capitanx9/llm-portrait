from typing import Any

from django_ratelimit.exceptions import Ratelimited
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    # django-ratelimit raises Ratelimited (a PermissionDenied subclass) when
    # block=True. DRF's default handler maps PermissionDenied to 403; we want
    # the more specific 429 so clients can retry instead of treating it as auth
    # failure.
    if isinstance(exc, Ratelimited):
        return Response({"detail": "Too many requests."}, status=429)
    return exception_handler(exc, context)
