from django.urls import path

from . import views

app_name = "ai"

urlpatterns = [
    path("process/", views.AIProcessView.as_view(), name="process"),
]
