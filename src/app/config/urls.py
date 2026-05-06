from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", include("app.core.urls")),
    path("api/", include("app.api.urls")),
]
