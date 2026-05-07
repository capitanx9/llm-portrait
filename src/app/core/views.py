from pathlib import Path

from django.conf import settings
from django.http import (
    FileResponse,
    HttpRequest,
    HttpResponse,
    HttpResponseBase,
    JsonResponse,
)


def health(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


def asyncapi_docs(request: HttpRequest) -> HttpResponseBase:
    """Serve the pre-rendered AsyncAPI HTML.

    The HTML is generated offline from `docs/api/ws/asyncapi.yaml` via
    `make asyncapi-build` and committed to the repo, the same way
    drf-spectacular's Swagger UI is served from a static page. We don't
    re-render at request time because the AsyncAPI HTML template needs
    a Node toolchain that we don't ship inside the Python image.
    """
    path = Path(settings.BASE_DIR) / "docs" / "api" / "ws" / "asyncapi.html"
    if not path.exists():
        return HttpResponse(
            "AsyncAPI docs not built. Run `make asyncapi-build` and commit "
            "the regenerated docs/api/ws/asyncapi.html.",
            status=503,
            content_type="text/plain",
        )
    return FileResponse(path.open("rb"), content_type="text/html")
