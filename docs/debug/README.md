# Debugging

Three independent surfaces. Any debugging session combines a subset
of them.

| Surface | What it gives you | Entry point |
|---|---|---|
| **Observation** (logs) | What happened on the server | `make logs-<service>` |
| **Pause** (debugpy) | Stop inside Python, inspect state | `make up-debug` + VS Code attach |
| **Trigger** (clients) | Hit the server from outside | Bruno, Swagger UI, curl |

The thread that ties them together is **`request_id`** — a 12-char
hex bound by middleware on every HTTP request and every WS
connection. Every server log line within that scope carries it. Grep
one id and you get the full lifecycle.

## How to read request_id

| Protocol | Where to find it |
|---|---|
| HTTP | `X-Request-ID` header on the response (visible in Bruno / Swagger / curl) |
| WS | `request_id=…` field on the `connect` log line in `make logs-ws` |

WS clients don't expose upgrade-response headers, so the id is
read from the server side instead. Once you have it, the workflow
is identical to HTTP.

## Configuration

| Env var | Default | Effect |
|---|---|---|
| `LOG_LEVEL` | `INFO` | `DEBUG` adds SQL queries and framework noise |
| `LOG_FORMAT` | `human` | `json` for log shippers (top-level keys per bound field) |
| `LOG_HTTP_BODY` | unset | `1` dumps request/response headers and JSON bodies on the access log. Bundled into `make up-debug`. |
| `DEBUGPY` | unset | `1` opens `:5678` for VS Code attach. Set by `make up-debug`. |
| `DEBUGPY_WAIT` | unset | `1` blocks boot until VS Code attaches. Set by `make up-debug-wait`. |

## Workflow

Read in order — each scenario builds on the previous one.

- [`workflow/0-setup.md`](workflow/0-setup.md) — Bring up the stack
  with demo data and the Bruno collection
- [`workflow/1-breakpoint.md`](workflow/1-breakpoint.md) — Stop
  inside a view with debugpy
- [`workflow/2-trace-http.md`](workflow/2-trace-http.md) — Find an
  HTTP failure by `request_id` in the logs
- [`workflow/3-trace-ws.md`](workflow/3-trace-ws.md) — Same workflow
  for WebSocket, with the one asymmetry called out
- [`workflow/4-services.md`](workflow/4-services.md) — Symptom →
  which `logs-<service>` to read (celery, db, redis, mailhog, ollama)
