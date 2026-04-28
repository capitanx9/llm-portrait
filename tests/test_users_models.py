import pytest
from django.db import IntegrityError

from app.users.models import UserFriends, UserProfile
from tests.factories import UserFactory

# ==============================================================================
# Create
# ==============================================================================


@pytest.mark.django_db
def test_user_profile_is_created_on_user_creation():
    user = UserFactory()
    assert UserProfile.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_userfriends_creates_reverse_link():
    a = UserFactory()
    b = UserFactory()
    UserFriends.objects.create(user=a, friend=b)
    assert UserFriends.objects.filter(user=b, friend=a).exists()


# ==============================================================================
# Constraints
# ==============================================================================


@pytest.mark.django_db
def test_userfriends_self_friendship_blocked():
    a = UserFactory()
    with pytest.raises(IntegrityError):
        UserFriends.objects.create(user=a, friend=a)


@pytest.mark.django_db
def test_userfriends_unique_pair():
    a = UserFactory()
    b = UserFactory()
    UserFriends.objects.create(user=a, friend=b)
    with pytest.raises(IntegrityError):
        UserFriends.objects.create(user=a, friend=b)


# ==============================================================================
# Delete
# ==============================================================================


@pytest.mark.django_db
def test_userfriends_delete_removes_reverse():
    a = UserFactory()
    b = UserFactory()
    fr = UserFriends.objects.create(user=a, friend=b)
    assert UserFriends.objects.filter(user=b, friend=a).exists()
    fr.delete()
    assert not UserFriends.objects.filter(user=b, friend=a).exists()


@pytest.mark.django_db
def test_user_cascade_delete_removes_profile_and_friendships():
    a = UserFactory()
    b = UserFactory()
    UserFriends.objects.create(user=a, friend=b)
    a_pk = a.pk
    a.delete()
    assert not UserProfile.objects.filter(user_id=a_pk).exists()
    assert not UserFriends.objects.filter(user_id=a_pk).exists()
    assert not UserFriends.objects.filter(friend_id=a_pk).exists()
