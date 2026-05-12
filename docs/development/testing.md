# Testing

What's tested, what's mocked, and what conventions the test suite follows.

## Stack

- **[pytest](https://docs.pytest.org)** — runner.
- **[pytest-django](https://pytest-django.readthedocs.io)** — `@pytest.mark.django_db`, `client` fixture, `mailoutbox` fixture, `settings` fixture.
- **[pytest-asyncio](https://pytest-asyncio.readthedocs.io)** — `@pytest.mark.asyncio` for the WebSocket consumer tests.
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

| File                       | Covers                                                                |
|----------------------------|-----------------------------------------------------------------------|
| `test_health.py`           | Legacy `/health/` endpoint returns 200 + `{"status": "ok"}`.          |
| `test_api.py`              | `/api/health/`, `/api/schema/`, `/api/docs/` reachability.            |
| `test_users_models.py`     | `User.email` uniqueness.                                              |
| `test_jwt_auth.py`         | Register, login, refresh, logout-then-reuse-fails, me-with-and-without-token. |
| `test_chat_models.py`      | `Room` and `Message` model constraints, name validator.               |
| `test_chat_rest.py`        | `RoomListCreateView`, `RoomMessagesView` — pagination, cursor, 401.   |
| `test_chat_ws.py`          | `ChatConsumer` auth gate (rejects anon), broadcast, invalid JSON.     |
| `test_chat_seeds.py`       | `seed_rooms` / `seed_messages` / `seed_all` / `flush_demo` idempotency. |
| `test_ai_graph.py`         | LangGraph nodes (`detect_lang`, `translate`, `summarize`, `fallback`), routing, end-to-end view with mocked LLM. |
| `test_email_tasks.py`      | Welcome email on register, via Celery eager mode.                     |
| `test_access_log.py`       | `HttpAccessLogMiddleware` format, severity-by-status, body dump, redaction. |

`conftest.py` is intentionally tiny — it exposes the `client` fixture and an autouse cache-clear fixture so rate-limit counters don't leak between tests.

## Factories

`tests/factories.py` ships one factory:

- **`UserFactory`** — creates a `User`. Important details:
  - `django_get_or_create = ("username",)` — calling the factory twice with the same username returns the same row, which keeps `factory.Sequence`-based tests stable across re-runs in the same process.
  - `skip_postgeneration_save = True` + a `post_generation` `password` hook — every factory user has the password `password123`. The hook calls `set_password(...)` and then `obj.save()` explicitly, avoiding factory-boy's deprecation warning about implicit saves.
  - Email auto-generated as `{username}@example.com`.

There are no profile or friendship factories — the corresponding models were removed in #47.

## Conventions

### `@pytest.mark.django_db`

Every test that touches the database has this marker (or takes the `db` fixture). pytest-django wraps the test in a transaction and rolls back at the end, keeping tests isolated.

```python
@pytest.mark.django_db
def test_login_returns_token_pair(client):
    ...
```

### `transaction=True` for `transaction.on_commit` callbacks

The welcome-email signal uses `transaction.on_commit(...)` to defer the Celery task until the user row is committed. With the default test transaction (rollback at the end), `on_commit` callbacks **never fire**, so the email never gets enqueued and the test fails.

The fix is `@pytest.mark.django_db(transaction=True)` — pytest-django then truncates tables instead of rolling back, which lets the transaction actually commit and `on_commit` callbacks run.

```python
@pytest.mark.django_db(transaction=True)
def test_welcome_email_sent_on_register(client, celery_eager):
    ...
```

This is in `test_email_tasks.py`. Tests that don't depend on `on_commit` use the cheaper default.

### Section comments

Test files group cases with `===`-bordered comment blocks. Purely a readability thing — keeps long files scrollable.

## What's mocked

### Ollama

Every LLM-related test patches at one of two levels — node-level for unit tests, view-level for end-to-end tests. No actual HTTP request to Ollama is ever made.

**Node-level** (`test_ai_graph.py`, most cases): patch the `_make_llm` factory inside `app.ai.nodes` so each node receives a fake `ChatOllama` that returns canned content.

```python
from app.ai import nodes

with patch.object(nodes, "_make_llm", return_value=_llm_returning("en")):
    result = detect_lang_node(state)
```

**View-level** (`test_ai_graph.py`, end-to-end cases): patch `run_graph` itself when the test only cares about the view's behaviour around the graph (request validation, rate-limit, response shape).

```python
with patch("app.ai.views.run_graph", return_value={"action": "translate", "translation": "hi"}):
    response = client.post("/api/ai/process/", ...)
```

CI doesn't have Ollama available — and even if it did, real generation is too slow for unit tests (1–10s warm, 30–60s cold).

### Celery

The `celery_eager` fixture in `test_email_tasks.py` flips the runtime to "execute tasks synchronously":

```python
@pytest.fixture
def celery_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
```

`CELERY_TASK_ALWAYS_EAGER = True` makes `task.delay(...)` run inline. `CELERY_TASK_EAGER_PROPAGATES = True` re-raises exceptions from the task instead of swallowing them. The fixture also swaps the email backend to `locmem` so `django.core.mail.outbox` captures messages.

This means the Celery worker is **never started** in tests. We're testing that the task gets enqueued and that its body works — not that the broker delivers it.

### Channels layer (WebSocket)

`test_chat_ws.py` overrides `CHANNEL_LAYERS` to `InMemoryChannelLayer` so the WS tests don't need a real Redis. `WebsocketCommunicator` from `channels.testing` drives the consumer directly through ASGI.

### Redis cache (rate limit)

`conftest.py` ships an autouse fixture that flushes the cache before and after each test:

```python
@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()
```

Without this, the per-user rate-limit counter on `/api/ai/process/` accumulates across tests and the rate-limit assertion becomes flaky depending on test order.

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

There is **no enforced coverage gate** in CI — tests must pass, but coverage % is informational. The current suite covers the "does it work" surface (models, views, signals, tasks, consumers, graph) and skips obvious dead-on-arrival paths (admin auto-renderers, error 500 handlers).

## Running tests locally

```bash
# Bring up the stack first (Postgres + Redis are required).
make up

# Run the whole suite.
make test

# Run with coverage.
make test-cov

# Run a single file.
docker compose -f docker-compose.dev.yml exec web python -m pytest tests/test_ai_graph.py -v

# Run a single test.
docker compose -f docker-compose.dev.yml exec web python -m pytest tests/test_chat_ws.py::test_anonymous_connect_rejected -v
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
