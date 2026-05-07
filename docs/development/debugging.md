# Debugging

Two independent tools for the same goal — figuring out what the running
backend is doing:

- **The step-debugger** (debugpy + VS Code). For pausing the live
  process and walking through code line by line. Useful when the bug is
  in branching logic or async flow and you need to see the program's
  state at a single moment.
- **Logging** (loguru). For everything else. A `logger.info(...)` plus a
  tailed service log answers most questions faster than attaching a
  debugger, and it's the only way to see what already happened.

Reach for whichever fits the question; they don't conflict and both
work in the running Docker stack without rebuilding.

---

# Part 1 — Step-debugger

## How attach mode works

Our backend runs as a long-lived **server** (Django) inside a container.
There is no "run with debugger" button that starts and debugs in one
click, because the server is already running by the time you want to
look at it. So the flow is split in two:

1. The **server side** opens a debug port. Inside the container,
   `debugpy.listen(:5678)` says "any IDE that connects here can drive
   me." The server then keeps serving requests as normal — debugpy is
   passive until somebody connects.

2. The **client side** is VS Code. It opens a TCP connection to that
   port. From that moment on, VS Code knows about your breakpoints and
   can pause the server's Python interpreter when one is hit.

Both sides have to be alive at the same time. The server side is what
`make up-debug` gives you. The client side is what the green ▶ button
in VS Code's *Run and Debug* panel gives you.

When you trigger a request afterwards (Swagger UI, browser, curl), it
flows through Django; if it hits a line with a breakpoint, debugpy
tells VS Code to pause and you see the frozen state in the editor.

## Workflow

### 1. Start the stack with debugpy enabled

```bash
make up-debug
```

This is `make up` with `DEBUGPY=1` set. The web container imports
`debugpy`, opens port `5678`, and disables Django's autoreload (it
plays badly with debugpy's path tracking). Without the flag none of
this happens and there is no overhead.

Verify it's listening:

```bash
make logs-web
```

You should see:

```
debugpy listening on :5678 (attach when you want)
Starting ASGI/Daphne development server at http://0.0.0.0:8000/
```

### 2. Set a breakpoint

Open the file you want to inspect (any file under `src/` or `tests/`).
Click on the **line number** of the line where execution should pause
— a red dot appears.

You can have many breakpoints. Click again to remove one.

### 3. Attach VS Code

`Cmd+Shift+D` (or the bug icon in the left sidebar) → the dropdown at
the top says *"Attach to web (Django) container"* → click the green ▶.

The status bar at the bottom of VS Code turns **orange** and a
floating debug toolbar appears. That's the signal you're attached.

### 4. Trigger the code

Whatever entry point exercises the line you care about:

- **REST endpoint** — open Swagger at <http://localhost:8000/api/docs/>,
  pick the operation, click *Try it out*, *Execute*. It hangs while
  Django is paused on your breakpoint.
- **Background work** — call the management command, fire the Celery
  task, etc. Same effect.

VS Code jumps to the file, highlights the paused line and shows the
current state.

### 5. Inspect and step

- Hover over any variable in the source — its current value pops up.
- The *Variables* panel on the left shows everything in scope.
- The *Debug Console* at the bottom evaluates arbitrary Python in the
  paused frame (`self.request.user.email`, `len(queryset)`, ...).

Toolbar shortcuts:

| Shortcut | Action |
|---|---|
| **F5** | Continue (run until the next breakpoint) |
| **F10** | Step over (next line, don't dive into function calls) |
| **F11** | Step into (go inside the function on this line) |
| **Shift+F11** | Step out (run until the current function returns) |
| **Shift+F5** | Detach the debugger |

Press F5 when you're done with a frame — the original request finishes
and Swagger (or the browser, or curl) finally receives its response.

### 6. Switch back to normal mode

```bash
make down
make up
```

Restores autoreload and turns the debugger off — that's how you want
the stack the rest of the time.

## "Wait until I attach" mode

If the code you want to break on runs only **once during boot**
(signals, app config, the first imports), the server's already past
that point by the time you click ▶ in VS Code. For these cases:

```bash
make up-debug-wait
```

The web process opens `:5678` and **blocks** until you attach. As soon
as VS Code connects, it continues. Useful for one-shot startup code.

## Path mappings

`.vscode/launch.json` maps the workspace root on your Mac to `/app`
inside the container so the breakpoints you set bind to the right
lines on the running process. There's nothing to configure unless you
change the working directory layout.

---

# Part 2 — Logging

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

### Dumping request/response bodies — dev only

When metadata isn't enough and you actually want to see the JSON the
frontend sent or what DRF returned, flip the env flag:

```bash
LOG_HTTP_BODY=1 make up
```

Each access line then gains four fields: `request_headers`,
`request_body`, `response_headers`, `response_body`. JSON bodies are
parsed structurally (in `LOG_FORMAT=json` you can grep them with `jq`),
other content types are reported as a one-line summary
(`<multipart/form-data, 12345 bytes>`).

Two layers of redaction run before logging:

- Headers `Authorization`, `Cookie`, `Set-Cookie`, `X-Api-Key`,
  `Proxy-Authorization`, `X-Auth-Token` → values replaced with `***`.
- JSON keys whose name contains `password`, `token`, `secret`,
  `api_key`, `access`, `refresh` (any depth) → values replaced with
  `***`.

Bodies larger than 4 KB are truncated.

### Why the body dump is dev-only

The flag is gated behind an explicit env var because, even with
redaction, dumping bodies into a permanent log stream is the wrong
choice in production:

- **PII leaks past the redactor.** Email addresses, friend usernames,
  generated tarot descriptions, free-text fields users type into the
  portrait — none of these match the sensitive-name list, but they
  shouldn't sit in CloudWatch retention forever either.
- **The redactor is a substring match, not a guarantee.** A new field
  named, say, `"answer"` that happens to carry a token would slip
  through silently. In dev that's a small risk you eat in exchange for
  speed. In prod the safer default is "log nothing about the body."
- **Volume and cost.** A 4 KB extra payload per request, multiplied by
  every request the server handles, is a real number on the log
  shipper's invoice and on disk usage.
- **Streaming and large responses.** The middleware reads
  `response.content`, which for a streaming response (or a future big
  download) would buffer the whole thing in memory just to log it.

So the production stance is: structured access lines (method/path/
status/duration/user/request_id) are always on, body dumps are off.
For one-off prod investigations, attach with the step-debugger or add
a one-line `logger.info` next to the suspicious code path and ship a
PR — both are auditable, while a hidden flag flipped on a live server
is not.

## Service log shortcuts

| Command | What |
|---|---|
| `make logs-web` | Django / gunicorn / daphne |
| `make logs-ws` | daphne / Channels (the dedicated WS service in dev) |
| `make logs-celery` | Celery worker |
| `make logs-db` | Postgres |

## Manual WS chat demo

Automated coverage of the WebSocket chat lives in
`tests/test_chat_ws.py` (auth, broadcast, isolation, invalid JSON,
persistence). When you want to *eyeball* the log output instead — see
`request_id` stitching across connect/message/disconnect, see what
fields `_handshake_fields()` extracts from a real client — there's a
helper:

```bash
make ws-demo
```

It registers two demo users (idempotent), grabs fresh JWTs, and prints
two ready-to-paste `websocat` commands — one with `User-Agent` /
`Origin` headers (so the connect log line shows the enriched
handshake fields), one bare (so you can see how the empty-fields
filter works).

Pair it with `make logs-ws` in another terminal. Requires
`brew install websocat`.

Override the defaults via env if you need different names/room:

```bash
WS_DEMO_USER_A=alice WS_DEMO_USER_B=bob WS_DEMO_ROOM=my-room make ws-demo
```
