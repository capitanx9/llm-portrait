from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "app.users"
    label = "users"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from . import signals  # noqa: F401
