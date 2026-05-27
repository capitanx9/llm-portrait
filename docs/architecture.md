# Architecture

## Dev compose

```
                                ┌──────────────┐
                                │   client     │  Bruno · curl · Swagger UI
                                └──────┬───────┘
                          REST  │      │  WS
                http://:8000   │      │  ws://:8001
                                ▼      ▼
                       ┌──────────┐   ┌──────────┐
                       │  web     │   │  ws      │
                       │ Django   │   │ daphne   │
                       │ runserver│   │ ASGI     │
                       └─┬──┬──┬──┘   └────┬─────┘
                         │  │  │           │
            ┌────────────┘  │  └────────┐  │
            │               │           │  │
            ▼               ▼           ▼  ▼
     ┌──────────┐   ┌──────────────┐   ┌──────────┐
     │ db       │   │ redis        │   │ ollama   │
     │ Postgres │   │ cache·broker │   │ Llama3.2 │
     │ 16       │   │ ·channels    │   │ :3b      │
     └──────────┘   └──────┬───────┘   └──────────┘
                           │ broker
                           ▼
                    ┌──────────────┐    SMTP    ┌──────────────┐
                    │ celery       ├───────────►│ mailhog      │
                    │ worker       │            │ UI :8025     │
                    └──────────────┘            └──────────────┘
```

Seven long-running services. `web` and `ws` share the same image but run different commands — Django's HTTP `runserver` on 8000 for REST, daphne ASGI on 8001 for WebSocket. They talk to the same Postgres, the same Redis (used for three different purposes — cache, Celery broker, Channels layer — on three logical DBs), and the same Ollama. A `celery` worker tags along to handle anything that shouldn't block the request cycle (welcome email today). Mailhog is the SMTP sink so outbound mail stops at <http://localhost:8025> instead of leaving the machine.

See [`docker-compose.dev.yml`](../docker-compose.dev.yml) for the full definition.

## Prod compose

```
                             internet
                                │
                                │ 80 / 443
                                ▼
                       ┌─────────────────┐
                       │ nginx           │  TLS, static, ACME challenge
                       │                 │  /        → web:8000
                       │                 │  /ws/     → ws:8001
                       │                 │  /static/ → /staticfiles/
                       └────┬────────┬───┘
                            │        │
                  REST/HTTP │        │ WS upgrade
                            ▼        ▼
                     ┌─────────┐  ┌─────────┐
                     │ web     │  │ ws      │
                     │ gunicorn│  │ daphne  │
                     └─┬──┬────┘  └────┬────┘
                       │  │            │
                       ▼  ▼            ▼
                    db, redis, ollama   ← same as dev
                              │
                              └── celery worker, mailhog
                                  (kept for the demo)

                       ┌─────────────────┐
                       │ certbot         │  renews Let's Encrypt every 12h
                       └─────────────────┘
```

The prod compose adds two services on top of dev: `nginx` and `certbot`. `nginx` is the single public entry point on port 443 — it terminates TLS, serves `/static/`, and proxies the rest by path: `/ws/*` to the ws container (with `proxy_http_version 1.1` and the `Upgrade`/`Connection` headers needed for the WebSocket handshake) and everything else to web. `certbot` runs in a loop and renews the certificate via the webroot challenge every 12 hours, sharing the cert with nginx through a named volume.

Mailhog is kept on prod intentionally — the demo doesn't need real outbound mail, and the UI gives a quick way to verify that emails are sent during a review session. Replacing it with SES/Postmark is a single env-var change (`EMAIL_HOST` / `EMAIL_BACKEND`).

The production frontend lives on a separate origin (CloudFront), not on the same host as the backend. REST and WebSocket are still served from `llm-portrait.gotdns.ch`; static assets are served from `*.cloudfront.net`. The split is intentional — see [`deployment/frontend.md`](deployment/frontend.md) for the CORS + WS-origin configuration and the DNS rationale behind the raw CloudFront URL.

See [`docker-compose.prod.yml`](../docker-compose.prod.yml) and [`docker/nginx.conf`](../docker/nginx.conf) for the full definitions.

## Service-by-service

### `web`

Django app, runs `manage.py runserver` in dev and `gunicorn` in prod (3 workers, 600s timeout). Image is built from `docker/Dockerfile` (multi-stage with `dev` and `prod` targets). Reads its config from `.env`. On startup it runs `migrate` automatically via `docker/entrypoint.dev.sh` / `docker/entrypoint.prod.sh`.

Hosts everything REST: `app.api` (auth endpoints, OpenAPI schema, Swagger UI), `app.chat` (room and message endpoints), `app.ai` (LangGraph endpoint), `app.core` (legacy `/health/`).

Code lives in [`src/app/`](../src/app). The Django project is `app.config`. Feature apps: `app.users` (custom `User` model), `app.chat` (rooms + messages), `app.ai` (LangGraph), `app.api` (REST shell + auth), `app.ws` (Channels consumers), `app.core` (cross-cutting middleware, request_id, access log).

### `ws`

Same image as `web`, started with `python -m daphne -b 0.0.0.0 -p 8001 app.config.asgi:application`. Hosts the ASGI app: the WebSocket consumer at `/ws/chat/<name>/` plus the static AsyncAPI viewer at `/ws/docs/`. Middleware stack on the websocket protocol: `OriginValidator → RequestIdMiddleware → JWTAuthMiddleware → URLRouter`. `OriginValidator` (Channels' built-in) whitelists handshakes by the `Origin` header against `WS_ALLOWED_ORIGINS`; cross-origin requests from anywhere outside the list are refused with HTTP 403 before auth runs. `JWTAuthMiddleware` reads `?token=…` from the query string and sets `scope["user"]`; the consumer rejects unauthenticated upgrades by closing before `accept()`, which surfaces as HTTP 403 to the client.

Lives separately from `web` because daphne and gunicorn have different process models (event-loop vs. forked workers) and Django doesn't recommend running both inside one container.

### `celery`

Same image as `web`, started with `python -m celery -A app.config worker`. Picks up tasks declared in `src/app/users/tasks.py`.
Today there is one task:

- `send_welcome_email(user_id)` — fired from a `post_save(User, created=True)` signal in [`src/app/users/signals.py`](../src/app/users/signals.py), wrapped in `transaction.on_commit(...)` so it only runs after the user row is committed.

Worker is started with `entrypoint: []` to skip the migrate step (only `web` runs migrations).

### `db`

`postgres:16-alpine`. Persistent volume `pgdata`. Healthcheck via `pg_isready`. Credentials come from `.env` (`DB_NAME`, `DB_USER`, `DB_PASSWORD`).

### `redis`

`redis:7-alpine`. Three unrelated uses on three logical DBs:

- **db `0`** — Celery broker (`CELERY_BROKER_URL=redis://redis:6379/0`).
- **db `1`** — Django cache backend, used by the `django-ratelimit` decorator on `/api/ai/process/` so the per-user limit holds across gunicorn workers (`REDIS_CACHE_URL=redis://redis:6379/1`).
- **db `2`** — Channels layer for cross-process WebSocket broadcast — a message sent to `chat_<room>` from one daphne process is fanned out to every connected client regardless of which process they handshook with (`REDIS_CHANNELS_URL=redis://redis:6379/2`).

### `mailhog`

`mailhog/mailhog:latest`. Two ports inside the network: `1025` for SMTP, `8025` for the web UI. The web UI is exposed to the host in dev. Emails just stop here.

### `ollama`

`ollama/ollama:latest`. Listens on `11434` inside the network. The model is stored in the `ollama_data` volume — pulled once with `make ollama-pull` (or manually on EC2) and cached forever.

LangChain's `ChatOllama` talks to it over HTTP from the LangGraph nodes. URL and model are configurable via `OLLAMA_URL` and `OLLAMA_MODEL`; node temperature is `AI_TASK_TEMPERATURE` (default 0.2, low because detect/translate/summarize want determinism).

### `nginx` (prod only)

Acts as the TLS endpoint. Two server blocks: one on `:80` for the ACME challenge plus a redirect to HTTPS, one on `:443` proxying by path. `/ws/` goes to `ws:8001` with WebSocket-upgrade headers and a 1-hour read timeout (chat connections are long-lived); everything else goes to `web:8000` with a 600s timeout — enough headroom for the LangGraph AI endpoint on a cold Ollama (first request after idle can hit 30–60s while the model loads).

### `certbot` (prod only)

Renews the Let's Encrypt cert every 12h. Cert lives in a named volume mounted into both `nginx` and `certbot`.

## Data flow: register → JWT pair

1. Client `POST /api/auth/register/` with `{username, email, password}`. `RegisterView` (DRF `CreateAPIView`) validates the payload through `RegisterSerializer`, creates the `User` row, and returns `201 Created`.
2. The `post_save(User, created=True)` signal in [`src/app/users/signals.py`](../src/app/users/signals.py) fires. It enqueues `send_welcome_email.delay(user.pk)` inside `transaction.on_commit(...)` so the task only runs after the row is committed.
3. Celery picks the task up off Redis and ships an email to Mailhog through SMTP.
4. Client `POST /api/auth/login/` with `{username, password}`. Returns `{access, refresh}` — `simplejwt`'s `TokenObtainPairView` signs both tokens.
5. Client stores both. The access token goes in `Authorization: Bearer …` on every protected REST call; the refresh token is used at `/api/auth/refresh/` when access expires (15 min) and added to the blacklist at `/api/auth/logout/`.

## Data flow: chat message broadcast

1. Client opens `wss://<host>/ws/chat/<room>/?token=<access>`. nginx forwards the upgrade to the `ws` container (daphne).
2. `JWTAuthMiddleware` (in [`src/app/ws/middleware.py`](../src/app/ws/middleware.py)) extracts `token` from the query string, validates it against simplejwt, and sets `scope["user"]`. Invalid token → `AnonymousUser`.
3. `ChatConsumer.connect()` (in [`src/app/ws/consumers.py`](../src/app/ws/consumers.py)) checks `scope["user"].is_authenticated`. Anonymous → `await self.close(code=4001)` before `accept()` — daphne surfaces this as HTTP 403 to the client. Authenticated → resolve the `Room` (`get_or_create`), join the channel group `chat_<room>`, `await self.accept()`.
4. Client sends `{"text": "hi"}`. `ChatConsumer.receive_json()` validates, writes a `Message` row (`room` + `sender` + `text`), and calls `channel_layer.group_send(f"chat_{room}", {"type": "chat.message", "id": …, "sender": …, "text": …, "created_at": …})`.
5. The Channels Redis layer (db `2`) fans the event out to every daphne process that has a connection in this group. Each consumer's `chat_message` handler ships the payload to its socket as JSON.
6. All clients in the room see the message immediately, including the original sender — there's no optimistic echo, so message ordering is whatever the server group_send order produces.

## Data flow: AI process (translate or summarize)

1. Client `POST /api/ai/process/` with `{action: "translate", message, target_language}` or `{action: "summarize", conversation: [...]}`. `Authorization: Bearer …` is required.
2. `AIProcessView` (in [`src/app/ai/views.py`](../src/app/ai/views.py)) is wrapped in `@ratelimit(key="user", rate=settings.LLM_RATE_LIMIT)`. Over the limit → 429.
3. Below the limit, the view calls `run_graph(state)` from [`src/app/ai/graph.py`](../src/app/ai/graph.py). The graph has four nodes:
   - `detect_lang` — LLM call, returns a language code; writes `state["source_language"]`.
   - `condition` — pure-Python router on `state["action"]`. `translate` → `translate_node`; `summarize` → `summarize_node`.
   - `translate_node` — LLM call with `target_language`; writes `state["translation"]`.
   - `summarize_node` — LLM call over the conversation (truncated to fit the model's context window); writes `state["summary"]`.
   - `fallback` — any node that raises is caught by the `_safe` wrapper; the graph routes to `fallback`, which writes `state["error"]` and `state["failed_node"]` and short-circuits to END.
4. Each LLM call is `ChatOllama(...)` against `OLLAMA_URL`, temperature `AI_TASK_TEMPERATURE` (default 0.2). Total time depends on Ollama warmth and model size — 1–10 seconds on a warm Llama3.2:3b, longer on cold start.
5. The view inspects the final state:
   - `state["error"]` present → 503 with `{"detail": "<error>"}`.
   - Otherwise → 200 with `{"action", "source_language"}` plus `"translation"` or `"summary"` depending on the action.
