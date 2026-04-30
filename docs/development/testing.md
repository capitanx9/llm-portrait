# Testing

What's tested, what's mocked, and what conventions the test suite follows.

## Stack

- **[pytest](https://docs.pytest.org)** — runner.
- **[pytest-django](https://pytest-django.readthedocs.io)** — `@pytest.mark.django_db`, `client` fixture, `mailoutbox` fixture, `settings` fixture.
- **[pytest-cov](https://pytest-cov.readthedocs.io)** — coverage report (only invoked manually via `make test-cov`).
- **[factory-boy](https://factoryboy.readthedocs.io)** + **[Faker](https://faker.readthedocs.io)** — model factories.

Configuration lives in `pyproject.toml` under `[tool.pytest.ini_options]`:

```toml
DJANGO_SETTINGS_MODULE = "app.config.settings.dev"
pythonpath = ["src"]
testpaths = ["tests"]
addopts = ["-ra", "--strict-markers", "--strict-config"]
```

## Layout

All tests live in [`tests/`](../../tests) at the repo root, **outside** `src/`. One file per domain:

| File                       | Covers                                                          |
|----------------------------|-----------------------------------------------------------------|
| `test_health.py`           | `/health/` endpoint returns 200 + `{"status": "ok"}`.           |
| `test_users_models.py`     | `User` / `UserProfile` / `UserFriends` models and signals.      |
| `test_landing.py`          | `/` rendering, anon vs authenticated routing.                   |
| `test_auth.py`             | allauth login / signup / logout, password validation, password-reset rendering. |
| `test_portrait_views.py`   | `/portrait/` GET + POST, profile form validation.               |
| `test_friends_views.py`    | `friend_add` and `friend_remove` views — happy path + edge cases (self, nonexistent, duplicate, others' rows). |
| `test_email_tasks.py`      | Welcome email on signup, password-reset email, both via Celery eager mode. |
| `test_llm.py`              | Prompt construction, Ollama call (mocked).                       |
| `test_generate_view.py`    | `/portrait/generate/` endpoint — auth, happy path with mocked LLM, error path, rate limit. |

`conftest.py` is intentionally tiny — it just exposes the `client` fixture by name so test files can use it without importing.

## Factories

`tests/factories.py` ships three factories:

- **`UserFactory`** — creates a `User`. Important details:
  - `django_get_or_create = ("username",)` — coexists with the `post_save(User)` signal that auto-creates a profile. Without this, two factories with the same username would race the signal.
  - `password` set via `factory.PostGenerationMethodCall("set_password", "password123")` — every factory user has the password `password123`.
  - Email auto-generated as `{username}@example.com`.
- **`UserProfileFactory`** — `django_get_or_create = ("user",)`. Same reason as above: the signal already created an empty profile, so the factory updates it instead of inserting a duplicate.
- **`UserFriendsFactory`** — straight subfactory pair.

Tests almost always use `UserFactory` directly. `UserProfileFactory` is rarely needed because the auto-created profile is already there.

## Conventions

### `@pytest.mark.django_db`

Every test that touches the database has this marker (or takes the `db` fixture). pytest-django wraps the test in a transaction and rolls back at the end, keeping tests isolated.

```python
@pytest.mark.django_db
def test_signup_creates_user_and_profile(client):
    ...
```

### `transaction=True` for `transaction.on_commit` callbacks

The welcome-email signal uses `transaction.on_commit(...)` to defer the Celery task until the user row is committed. With the default test transaction (rollback at the end), `on_commit` callbacks **never fire**, so the email never gets enqueued and the test fails.

The fix is `@pytest.mark.django_db(transaction=True)` — pytest-django then truncates tables instead of rolling back, which lets the transaction actually commit and `on_commit` callbacks run.

```python
@pytest.mark.django_db(transaction=True)
def test_welcome_email_sent_on_signup(client, celery_eager):
    ...
```

This is in `test_email_tasks.py::test_welcome_email_sent_on_signup`. Tests that don't depend on `on_commit` use the cheaper default.

### Section comments

Test files group cases with `===`-bordered comment blocks:

```python
# ==============================================================================
# Add
# ==============================================================================

@pytest.mark.django_db
def test_friend_add_creates_friendship(client):
    ...
```

This is purely a readability thing — the file scrolls cleanly when there are 5–10 tests in it.

## What's mocked

### Ollama

Every LLM-related test patches `app.users.views.generate_portrait` (or `app.users.llm.ChatOllama`) so no actual HTTP request to Ollama is ever made:

```python
with patch("app.users.views.generate_portrait", return_value="test description"):
    response = client.post("/portrait/generate/")
```

CI doesn't have Ollama available — and even if it did, real generation is too slow for unit tests (1–3 min per call).

### Celery

A `celery_eager` fixture in `test_email_tasks.py` and `test_generate_view.py` flips the runtime to "execute tasks synchronously":

```python
@pytest.fixture
def celery_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
```

`CELERY_TASK_ALWAYS_EAGER = True` makes `task.delay(...)` run inline. `CELERY_TASK_EAGER_PROPAGATES = True` re-raises exceptions from the task instead of swallowing them. The fixture also swaps the email backend to `locmem` so `django.core.mail.outbox` captures messages.

This means the Celery worker is **never started** in tests. We're testing that the task gets enqueued and that its body works — not that the broker delivers it.

### Redis cache (rate limit)

`test_generate_view.py` has an autouse fixture that flushes the cache before and after each test:

```python
@pytest.fixture(autouse=True)
def clear_ratelimit_cache():
    cache.clear()
    yield
    cache.clear()
```

Without this, the rate-limit counter accumulates across tests and `test_generate_rate_limit_after_3_calls` becomes flaky.

### `request.user`-cached related objects

After `profile.save()` you might still see stale data via `user.profile.<field>`, because Django caches the related object on the user instance. Inside tests this looks like "I just saved arcana=magician but the prompt builder still sees blank".

The fix is `user.refresh_from_db()` between the save and the read:

```python
profile.arcana = "magician"
profile.save()

user.refresh_from_db()
prompt = build_portrait_prompt(user)
```

This is documented in `test_llm.py::test_build_portrait_prompt_includes_all_fields`.

## Coverage

The pyproject already wires up `[tool.coverage.run]`:

```toml
source = ["src"]
branch = true
omit = ["*/migrations/*", "*/settings/*", "*/tests/*", "*/__init__.py", "*/manage.py", "*/wsgi.py", "*/asgi.py"]
```

Run with:

```bash
make test-cov
```

There is **no enforced coverage gate** in CI — tests must pass, but coverage % is informational. The current suite covers the "does it work" surface (models, views, signals, tasks) and skips obvious dead-on-arrival paths (admin auto-renderers, error 500 handlers).

## Running tests locally

```bash
# Bring up the stack first (Postgres + Redis are required).
make up

# Run the whole suite.
make test

# Run with coverage.
make test-cov

# Run a single file.
docker compose -f docker-compose.dev.yml exec web python -m pytest tests/test_llm.py -v

# Run a single test.
docker compose -f docker-compose.dev.yml exec web python -m pytest tests/test_llm.py::test_generate_portrait_calls_ollama -v
```

## Running tests in CI

CI uses GitHub Actions services for Postgres and Redis (so no Docker-in-Docker). The `test` job in `.github/workflows/ci.yml`:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    ports: ["5432:5432"]
    options: >-
      --health-cmd "pg_isready -U app -d llm_portrait"
      --health-interval 5s ...
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    options: >-
      --health-cmd "redis-cli ping" ...
```

…and the env block hard-codes `DATABASE_URL=postgres://app:app@localhost:5432/...`, `CELERY_BROKER_URL=redis://localhost:6379/0`, `REDIS_CACHE_URL=redis://localhost:6379/1`. See [`ci-cd.md`](./ci-cd.md) for the full workflow walkthrough.
