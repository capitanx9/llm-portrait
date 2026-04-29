from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("portrait/", views.portrait_stub, name="portrait"),
]
