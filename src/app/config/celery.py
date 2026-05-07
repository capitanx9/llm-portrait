import os

from celery import Celery
from celery.signals import setup_logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.config.settings.dev")

# Celery worker is its own process (not `manage.py`), so it doesn't get
# loguru wired up via the manage entry point. Do it here so the worker's
# task logs share the same shape as web.
from app.config.logging import configure_logging

configure_logging()

app = Celery("llm_portrait")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@setup_logging.connect
def _configure_celery_logging(**_kwargs: object) -> None:
    """Block Celery's own logging setup and reuse the loguru pipeline.

    Without this, Celery's worker bootstrap calls `setup_logging_subsystem`
    which attaches its own StreamHandler to the `celery.*` loggers and
    rewrites the format — undoing the InterceptHandler we installed at
    process start. Connecting an empty handler to the `setup_logging`
    signal tells Celery "logging is already configured, leave it alone."
    Records still flow through stdlib root → InterceptHandler → loguru,
    so worker startup banners and per-task lines come out in the same
    shape as the web service.
    """
    configure_logging()
