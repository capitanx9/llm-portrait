import pytest

from app.users.models import UserFriends
from tests.factories import UserFactory

# ==============================================================================
# Add
# ==============================================================================


@pytest.mark.django_db
def test_friend_add_creates_friendship(client):
    alice = UserFactory(username="alice")
    bob = UserFactory(username="bob")
    client.force_login(alice)

    response = client.post(f"/portrait/friends/{bob.pk}/add/")
    assert response.status_code == 302
    assert UserFriends.objects.filter(user=alice, friend=bob).exists()
    assert UserFriends.objects.filter(user=bob, friend=alice).exists()


@pytest.mark.django_db
def test_friend_add_self_fails(client):
    alice = UserFactory(username="alice")
    client.force_login(alice)

    response = client.post(f"/portrait/friends/{alice.pk}/add/")
    assert response.status_code == 302
    assert not UserFriends.objects.filter(user=alice).exists()


@pytest.mark.django_db
def test_friend_add_nonexistent_user_404(client):
    alice = UserFactory(username="alice")
    client.force_login(alice)

    response = client.post("/portrait/friends/99999/add/")
    assert response.status_code == 404
    assert not UserFriends.objects.filter(user=alice).exists()


@pytest.mark.django_db
def test_friend_add_existing_friend_no_duplicate(client):
    alice = UserFactory(username="alice")
    bob = UserFactory(username="bob")
    UserFriends.objects.create(user=alice, friend=bob)
    client.force_login(alice)

    response = client.post(f"/portrait/friends/{bob.pk}/add/")
    assert response.status_code == 302
    assert UserFriends.objects.filter(user=alice, friend=bob).count() == 1


# ==============================================================================
# Remove
# ==============================================================================


@pytest.mark.django_db
def test_friend_remove_deletes_friendship(client):
    alice = UserFactory(username="alice")
    bob = UserFactory(username="bob")
    friendship = UserFriends.objects.create(user=alice, friend=bob)
    client.force_login(alice)

    response = client.post(f"/portrait/friends/{friendship.pk}/remove/")
    assert response.status_code == 302
    assert not UserFriends.objects.filter(user=alice, friend=bob).exists()
    assert not UserFriends.objects.filter(user=bob, friend=alice).exists()


@pytest.mark.django_db
def test_friend_remove_others_friendship_404(client):
    alice = UserFactory(username="alice")
    bob = UserFactory(username="bob")
    carol = UserFactory(username="carol")
    bobs_friendship = UserFriends.objects.create(user=bob, friend=carol)
    client.force_login(alice)

    response = client.post(f"/portrait/friends/{bobs_friendship.pk}/remove/")
    assert response.status_code == 404
    assert UserFriends.objects.filter(pk=bobs_friendship.pk).exists()
