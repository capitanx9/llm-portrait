import pytest
from django.core import mail

from tests.factories import UserFactory


@pytest.fixture
def celery_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


# ==============================================================================
# Welcome email
# ==============================================================================


@pytest.mark.django_db(transaction=True)
def test_welcome_email_sent_on_signup(client, celery_eager):
    response = client.post(
        "/accounts/signup/",
        {
            "username": "newuser",
            "email": "newuser@example.com",
            "password1": "pass1234",
            "password2": "pass1234",
        },
    )
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["newuser@example.com"]
    assert "Добро пожаловать" in mail.outbox[0].subject


# ==============================================================================
# Password reset email
# ==============================================================================


@pytest.mark.django_db
def test_password_reset_email_sent(client, celery_eager):
    user = UserFactory(email="alice@example.com")
    mail.outbox = []
    response = client.post("/accounts/password/reset/", {"email": user.email})
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]
