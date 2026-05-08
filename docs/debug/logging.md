# Logging (loguru)

How log records flow through the project, what fields you get, and
how to use them to trace a single request across web → worker → email.

For the other debug surfaces, see:

- [`breakpoints.md`](breakpoints.md) — VS Code attach mode, debugpy
- [`http.md`](http.md) — Swagger UI as a debugging tool
- [`ws.md`](ws.md) — `make ws-demo`, Bruno, reading `make logs-ws`

## Why loguru, and what it gives us

Stdlib `logging` is fine for a single library, but a Django project
runs **at least four frameworks at the same time** that each emit log
records: Django itself, DRF, Channels (with daphne), Celery, plus
gunicorn in production. By default each of them attaches its own
`StreamHandler`, picks its own format, and fights for stdout. The
result is three different log shapes mixed together and every
access-line printed twice — one of which we hit and fixed in this
project.

We replaced that with **one** sink: [loguru](https://loguru.readthedocs.io/).
The payoff:

- **One consistent line shape** for every framework, so the
  human-readable log in dev and the JSON log in prod each look like a
  single stream instead of a collage.
- **Built-in colored output** in dev (one fewer dependency than
  Django's debug console plus `colorlog`).
- **Native JSON serialization** in prod — every record becomes one
  object that CloudWatch / Loki / Promtail can parse without a custom
  decoder.
- **`logger.bind()` / `logger.contextualize()`** for attaching
  per-request metadata (request id, user) without touching the call
  sites that actually emit the log.

## How the wiring works in this project

```
                      ┌──────────────────────────────┐
 manage.py            │                              │
 wsgi.py    ───────►  │  configure_logging() once    │
 asgi.py              │  (app.config.logging)        │
 celery.py            │                              │
                      └──────────────┬───────────────┘
                                     │
                                     ▼
            ┌─────────────────────────────────────────────┐
            │  loguru.add(stdout, format=human|json)      │
            │  logging.basicConfig(handlers=[             │
            │      InterceptHandler                       │
            │  ], level=0, force=True)                    │
            └────────────────┬────────────────────────────┘
                             │
       ┌─────────────────────┼─────────────────────┐
       │                     │                     │
       ▼                     ▼                     ▼
 stdlib logging         loguru.info(...)     Django LOGGING
 (Django, DRF,          calls in our         dict neutralises
 daphne, Celery,        own code             django/daphne
 third-party libs)                           per-logger handlers
       │                     │                     │
       └─────────────────────┴─────────────────────┘
                             │
                             ▼
                     One unified stream
                     to stdout (Docker logs)
```

Three pieces make it click together:

1. **`app.config.logging.configure_logging()`** is called from every
   process entry point — `manage.py` for the runserver / management
   commands, `wsgi.py` for gunicorn in prod, `asgi.py` for daphne, and
   `celery.py` for the worker. Each long-lived process gets the sink
   set up *before* Django boots, so the very first log line a framework
   emits is already going through loguru.

2. **`InterceptHandler`** is a 15-line `logging.Handler` subclass
   installed at the **root** stdlib logger. Every `logging.getLogger(...)`
   in Django, DRF, daphne, Celery propagates up to root by default;
   from there our handler converts each `LogRecord` into a
   `logger.opt(...).log(...)` call so loguru gets it in its native
   shape.

3. **`LOGGING` dict in `settings/base.py`** does just one job: zero out
   the `StreamHandler` that Django ships on the `"django"` logger and
   the equivalent on `daphne.management.commands.runserver` /
   `django.channels.server` / `django.request`. Without this step those
   loggers would print their own line *and* propagate to root — every
   access line would appear twice.

The middleware layer adds the per-request context:

- **`app.core.middleware.RequestIdMiddleware`** generates (or accepts
  via `X-Request-ID`) a 12-char id, calls
  `logger.contextualize(request_id=...)`, and echoes the id back as a
  response header. Anything logged inside the wrapped `get_response`
  call carries that id.
- **`app.ws.middleware.RequestIdMiddleware`** does the same for
  WebSocket connections, where there's no Django middleware chain.
- **`app.core.middleware.HttpAccessLogMiddleware`** writes one
  structured access line per request (more on it below).

## What this gives you in practice

### Format

Two formats, switched by env var `LOG_FORMAT`:

- `human` (default in dev) — colored, one line per record. Any
  structured fields you bind on the call (`logger.info("...",
  room=x, user=y)`) are auto-rendered as `key=value` pairs:

  ```
  2026-05-07 10:59:45.969 | INFO     | app.ws.consumers:receive_json:98 | request_id=a1b2c3d4 | room=ws-debug user=wsbob length=13 | ws message
  ```

  This is done by a `format=` callable in `app.config.logging` that
  inspects each record's `extra` dict, so you don't need to list new
  fields in a format string up front.

- `json` (set in prod) — one JSON object per record, ready for log
  shippers (CloudWatch, Loki, etc.). The same bound fields become
  top-level keys, so structured queries are possible without parsing
  free text.

Set `LOG_LEVEL` to `DEBUG` when you want SQL queries and noisy
internals; default is `INFO`.

### Writing logs

Use loguru directly anywhere in `src/`:

```python
from loguru import logger

logger.info("user signed up", user_id=user.id)
logger.exception("ollama call failed")  # captures the traceback
logger.bind(view="generate_portrait").warning("fallback triggered")
```

Stdlib calls in third-party libs go through the InterceptHandler and
end up in the same stream — you don't have to do anything special.

### Request id traceability

Every HTTP request and WebSocket connection gets a short `request_id`.
It's:

- attached to every log line emitted while the request runs;
- echoed back as the `X-Request-ID` response header so a frontend (or
  `curl -i`) can quote it when reporting a bug;
- read from an incoming `X-Request-ID` header if the caller already
  supplied one, which lets you correlate logs across services.

Grep one id and you get the entry log, the SQL queries, the signal
fires, the Celery task pickup, and the email send for that one
request:

```bash
make logs-web | grep a1b2c3d4
```

### Access log

`HttpAccessLogMiddleware` writes one structured line per HTTP request
with method, path, status, duration_ms, user_id, view_name, client_ip
and request_id. Severity follows the status code:

| Status | Level |
|---|---|
| 2xx / 3xx | INFO |
| 4xx | WARNING |
| 5xx | ERROR |

So `grep WARNING` already surfaces every failed request without further
filters, and `grep ERROR` is the smoke alarm.

For HTTP-specific debugging tricks (Swagger, body dump examples), see
[`http.md`](http.md). For WS-specific log reading, see [`ws.md`](ws.md).

## Service log shortcuts

| Command | What |
|---|---|
| `make logs-web` | Django / gunicorn / daphne |
| `make logs-ws` | daphne / Channels (the dedicated WS service in dev) |
| `make logs-celery` | Celery worker |
| `make logs-db` | Postgres |
