import pytest
from django.db import IntegrityError

from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_email_unique():
    UserFactory(email="dup@example.com")
    with pytest.raises(IntegrityError):
        UserFactory(email="dup@example.com")
