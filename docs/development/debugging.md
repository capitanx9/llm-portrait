# Debugging

How to step through the code running inside Docker from VS Code.

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
⚙️  debugpy listening on :5678 (attach when you want)
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

## When not to use the debugger

For most bugs a `logger.info(...)` plus a tailed log of the right
service is faster than attaching:

```bash
make logs-web        # Django / gunicorn / daphne
make logs-ws         # daphne / Channels
make logs-celery     # Celery worker
make logs-db         # Postgres
```

Reach for the debugger when the bug is in branching logic, async
flow, or when you genuinely need to walk a complex object live.

## Logging

Logs go through **loguru** — Django, DRF, Channels, daphne, Celery,
gunicorn all funnel into one stream with consistent formatting. In the
code use loguru directly:

```python
from loguru import logger

logger.info("user signed up", extra={"user_id": user.id})
logger.exception("ollama call failed")  # captures the traceback
```

Anything that still uses stdlib `logging.getLogger(...)` (third-party
libs) is intercepted at the root logger and reformatted, so it shows up
in the same stream.

### Format

Two formats, switched by env var `LOG_FORMAT`:

- `human` (default in dev) — colored, one line per record:

  ```
  2026-05-07 10:59:45.969 | INFO     | app.users.views:generate:42 | request_id=a1b2c3d4 | user signed up
  ```

- `json` (set in prod) — one JSON object per record, ready for log
  shippers (CloudWatch, Loki, etc.).

Set `LOG_LEVEL` to `DEBUG` when you want SQL queries and the noisy
internals; default is `INFO`.

### Request id

Every HTTP request and every WebSocket connection gets a short
`request_id` (12 hex chars). It's:

- attached to every log line emitted while the request runs
  (`logger.contextualize(request_id=...)` in
  `app.core.middleware.RequestIdMiddleware` for HTTP and
  `app.ws.middleware.RequestIdMiddleware` for WS);
- echoed back as the `X-Request-ID` response header so a frontend (or
  curl with `-i`) can quote it when reporting a bug;
- read from an incoming `X-Request-ID` header if the caller already
  supplies one — useful for correlating across services.

Grep one id and you get the entry log, the SQL queries, the signal
fires, the Celery task pickup, and the email send for that one request:

```bash
make logs-web | grep a1b2c3d4
```

### Access log

`HttpAccessLogMiddleware` writes one structured line per HTTP request
with method, path, status, duration, user, view name, client IP and
request id. Severity follows the status code: 2xx/3xx → INFO, 4xx →
WARNING, 5xx → ERROR — so `grep WARNING` already gives you every failed
request without further filters.

### Dumping request/response bodies (dev only)

When metadata isn't enough — you want to see the JSON the frontend
actually sent, or what DRF returned — flip the env flag:

```bash
LOG_HTTP_BODY=1 make up
```

Each access line gains four fields: `request_headers`, `request_body`,
`response_headers`, `response_body`. JSON bodies are parsed structurally
(in `LOG_FORMAT=json` you can grep them with `jq`), other content types
are reported as a one-line summary (`<multipart/form-data, 12345
bytes>`).

Two layers of redaction run before logging:

- Headers `Authorization`, `Cookie`, `Set-Cookie`, `X-Api-Key`,
  `Proxy-Authorization`, `X-Auth-Token` → values replaced with `***`.
- JSON keys whose name contains `password`, `token`, `secret`, `api_key`,
  `access`, `refresh` (any depth) → values replaced with `***`.

Bodies larger than 4 KB are truncated and the line is tagged
`"_truncated": true`.

**Never set `LOG_HTTP_BODY=1` in production.** Even with redaction the
dump still contains email addresses, friend lists, generated portraits
and other payload data that has no business being on disk forever.
