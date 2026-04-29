import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.config.settings.dev")

app = Celery("llm_portrait")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
