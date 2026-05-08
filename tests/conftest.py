import pytest
from django.core.cache import cache
from django.test import Client


@pytest.fixture
def client() -> Client:
    return Client()


@pytest.fixture(autouse=True)
def clear_ratelimit_cache() -> None:
    # django-ratelimit stores counters in the Django cache (Redis here);
    # without clearing between tests, a previous test's POSTs count against
    # the next, making the ratelimit test flaky and leaking state.
    cache.clear()
