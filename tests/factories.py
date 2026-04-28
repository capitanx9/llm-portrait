import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory

from app.users.models import UserFriends, UserProfile

User = get_user_model()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "password123")


class UserProfileFactory(DjangoModelFactory):
    class Meta:
        model = UserProfile
        django_get_or_create = ("user",)

    user = factory.SubFactory(UserFactory)
    age = factory.Faker("pyint", min_value=18, max_value=80)
    location = factory.Faker("city")
    arcana = "fool"
    shadow = factory.Faker("sentence")
    quest = factory.Faker("sentence")
    curse = factory.Faker("sentence")


class UserFriendsFactory(DjangoModelFactory):
    class Meta:
        model = UserFriends

    user = factory.SubFactory(UserFactory)
    friend = factory.SubFactory(UserFactory)
