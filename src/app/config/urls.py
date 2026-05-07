from django.contrib import admin
from django.urls import include, path

from app.core.views import asyncapi_docs

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", include("app.core.urls")),
    path("api/", include("app.api.urls")),
    # Symmetric to /api/docs/ (drf-spectacular Swagger UI) but for the
    # WebSocket side. The HTML is pre-rendered from docs/api/ws/asyncapi.yaml.
    path("ws/docs/", asyncapi_docs, name="asyncapi-docs"),
]
