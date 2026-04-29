from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("portrait/", views.PortraitView.as_view(), name="portrait"),
    path("portrait/generate/", views.generate, name="generate"),
    path("portrait/friends/<int:user_id>/add/", views.friend_add, name="friend_add"),
    path("portrait/friends/<int:pk>/remove/", views.friend_remove, name="friend_remove"),
]
