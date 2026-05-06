import pytest
from django.contrib.auth import get_user_model
from django.core import mail

User = get_user_model()


@pytest.fixture
def celery_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


# ==============================================================================
# Welcome email
# ==============================================================================


@pytest.mark.django_db(transaction=True)
def test_welcome_email_sent_when_user_created_with_email(celery_eager):
    User.objects.create_user(username="alice", email="alice@example.com", password="pass1234")

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["alice@example.com"]
    assert "Добро пожаловать" in mail.outbox[0].subject


@pytest.mark.django_db(transaction=True)
def test_welcome_email_skipped_when_email_blank(celery_eager):
    User.objects.create_user(username="root", email="", password="pass1234")

    assert mail.outbox == []
