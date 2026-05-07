import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.config.settings.dev")

# Celery worker is its own process (not `manage.py`), so it doesn't get
# loguru wired up via the manage entry point. Do it here so the worker's
# task logs share the same shape as web.
from app.config.logging import configure_logging

configure_logging()

app = Celery("llm_portrait")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
