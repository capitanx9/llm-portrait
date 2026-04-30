# Architecture

## Dev compose

```
                                ┌──────────────┐
                                │   browser    │
                                └──────┬───────┘
                                       │ http://localhost:8000
                                       ▼
                              ┌──────────────────┐
                              │  web (Django,    │
                              │  runserver)      │
                              └─┬───┬───┬────┬───┘
                                │   │   │    │
                ┌───────────────┘   │   │    └──────────────────┐
                │                   │   │                       │
                ▼                   ▼   ▼                       ▼
         ┌─────────────┐    ┌──────────────┐           ┌────────────────┐
         │ db          │    │ redis        │           │ ollama         │
         │ Postgres 16 │    │ broker + cache│          │ Llama3.2:3b    │
         └─────────────┘    └──────┬───────┘           └────────────────┘
                                   │
                                   ▼
                            ┌─────────────┐    SMTP    ┌─────────────┐
                            │ celery      ├───────────►│ mailhog     │
                            │ worker      │            │ UI :8025    │
                            └─────────────┘            └─────────────┘
```

Five long-running services: `web`, `db`, `redis`, `mailhog`, `ollama`, plus a `celery` worker that listens on Redis and shares the same code as `web`. Mailhog is an SMTP sink, so emails sent from Django end up in its UI at <http://localhost:8025> instead of going out to the world.

See [`docker-compose.dev.yml`](../docker-compose.dev.yml) for the full definition.

## Prod compose

```
            internet
               │
               │ 80 / 443
               ▼
        ┌─────────────┐
        │ nginx       │  TLS termination, static, ACME challenge
        └──────┬──────┘
               │ proxy_pass http://web:8000
               ▼
        ┌─────────────┐
        │ web         │  gunicorn, 3 workers
        │ (Django)    │
        └─┬───┬───┬───┘
          │   │   │
          ▼   ▼   ▼
       db  redis  ollama   ← same as dev
                  │
                  └── celery worker, mailhog (kept for the demo)

        ┌─────────────┐
        │ certbot     │  renews Let's Encrypt cert in a loop
        └─────────────┘
```

The prod compose adds two services on top of dev:

- `nginx` — TLS terminator, serves `/static/`, forwards everything else to `web` over the internal network. The vhost answers on `llm-portrait.gotdns.ch`.
- `certbot` — runs in a loop, renews the certificate every 12h via the webroot challenge. The cert is shared with `nginx` through a named volume.

Mailhog is kept on prod intentionally — the brief demo doesn't need real outbound mail, and the UI gives a quick way to verify that emails are sent during a review session. Replacing it with SES/Postmark is a single env-var change (`EMAIL_HOST` / `EMAIL_BACKEND`).

See [`docker-compose.prod.yml`](../docker-compose.prod.yml) and [`docker/nginx.conf`](../docker/nginx.conf) for the full definitions.

## Service-by-service

### `web`

Django app, runs `manage.py runserver` in dev and `gunicorn` in prod (3 workers, 600s timeout). Image is built from `docker/Dockerfile` (multi-stage with `dev` and `prod` targets). Reads its config from `.env`. On startup it runs `migrate` automatically via `docker/entrypoint.dev.sh` / `docker/entrypoint.prod.sh`.

Code lives in [`src/app/`](../src/app). The Django project is `app.config`, with `app.users` as the only feature app and `app.core` for the `/health/` endpoint.

### `celery`

Same image as `web`, started with `python -m celery -A app.config worker`. Picks up tasks declared in `src/app/users/tasks.py`. Today there are two tasks:

- `send_welcome_email(user_id)` — fired from the `allauth` `user_signed_up` signal.
- `send_email_async(subject, body, from_email, recipients)` — generic helper that the custom allauth account adapter pushes all transactional emails through (so password reset goes through Celery without a per-template task).

Worker is started with `entrypoint: []` to skip the migrate step (only `web` runs migrations).

### `db`

`postgres:16-alpine`. Persistent volume `pgdata`. Healthcheck via `pg_isready`. Credentials come from `.env` (`DB_NAME`, `DB_USER`, `DB_PASSWORD`).

### `redis`

`redis:7-alpine`. Used for two unrelated things on logical-DB level:

- **db `0`** — Celery broker (`CELERY_BROKER_URL=redis://redis:6379/0`).
- **db `1`** — Django cache backend, used by the `django-ratelimit` decorator on the LLM endpoint and by allauth's internal rate limits (`REDIS_CACHE_URL=redis://redis:6379/1`).

### `mailhog`

`mailhog/mailhog:latest`. Two ports inside the network: `1025` for SMTP, `8025` for the web UI. The web UI is exposed to the host in dev. Emails just stop here.

### `ollama`

`ollama/ollama:latest`. Listens on `11434` inside the network. The model is stored in the `ollama_data` volume — pulled once with `make ollama-pull` (or manually on EC2) and cached forever.

LangChain's `ChatOllama` talks to it over HTTP. URL and model are configurable via `OLLAMA_URL` and `OLLAMA_MODEL`.

### `nginx` (prod only)

Acts as the TLS endpoint. Two server blocks: one on `:80` for the ACME challenge plus a redirect to HTTPS, one on `:443` proxying to `web`. Long timeouts (`proxy_read_timeout 600s`) — LLM generation on a small EC2 takes 1–3 minutes.

### `certbot` (prod only)

Renews the Let's Encrypt cert every 12h. Cert lives in a named volume mounted into both `nginx` and `certbot`.

## Data flow: signup → welcome email

1. User submits the signup form → `POST /accounts/signup/` (handled by allauth).
2. Django creates the `User`, the `post_save(User)` signal in [`src/app/users/signals.py`](../src/app/users/signals.py) auto-creates an empty `UserProfile`.
3. Allauth fires the `user_signed_up` signal. The handler in the same file enqueues `send_welcome_email.delay(user.pk)`. The call is wrapped in `transaction.on_commit(...)` so the task only runs after the user row is committed.
4. The Celery worker picks the task up off Redis, renders the email body, and `send_mail()` ships it through SMTP to Mailhog (or the configured SMTP server).
5. User is redirected to `/portrait/` and sees the empty profile form.

## Data flow: generate portrait

1. User clicks "✨ Сгенерировать портрет" on `/portrait/` → `POST /portrait/generate/`.
2. The view is decorated with `@login_required`, `@require_POST`, and `@ratelimit(key="user", rate=settings.LLM_RATE_LIMIT, block=False)`. If the user is over the limit, the view sees `request.limited == True`, flashes an error, and redirects back.
3. Otherwise it calls `generate_portrait(user)` from [`src/app/users/llm.py`](../src/app/users/llm.py). That function:
   - Loads the user's profile and friends' arcanas in one query (`select_related("friend__profile")`).
   - Builds a `ChatPromptTemplate` with a system prompt (mystical narrator, Russian only, 80–120 words) and a user prompt (the tarot fields).
   - Invokes `ChatOllama(...)` with a 600s client timeout. The HTTP call goes to `http://ollama:11434/api/chat`.
4. Ollama returns the generated text. The view stores it on `profile.description` (with `update_fields=["description", "updated_at"]` to skip touching the rest of the row), flashes a success message, and redirects to `/portrait/`.
5. The browser reloads the page and shows the description in the "Описание (от ИИ)" block.
