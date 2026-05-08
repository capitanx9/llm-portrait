# Debugging

Debugging always pairs two sides:

- **Client-side** — where the request comes from. Tools live under
  [`../api/`](../api/) (Bruno, Swagger UI, curl).
- **Server-side** — what the backend does with the request. Tools
  live here.

The thread that connects them is `X-Request-ID` / `request_id` —
returned in every HTTP response, bound on every WS handshake, and
present on every server log line within the same scope.

## Tools

| Tool | Side | Purpose |
|---|---|---|
| Bruno, Swagger UI, curl | client | Issue REST and WS requests |
| `make logs-*` | server | Tail per-service logs |
| loguru `request_id` | both | One id ties client request to server log lines |
| debugpy | server | Step through Python in VS Code |
| `LOG_HTTP_BODY=1` | server | Dump request/response bodies on the access log |

## How it works (architecture)

- [`architecture/loguru.md`](architecture/loguru.md) — log sink,
  request_id propagation, body dump, redaction, formats
- [`architecture/debugpy.md`](architecture/debugpy.md) — attach mode
  wiring, env vars, autoreload caveat

## How to use it (workflow)

- [`workflow/logs.md`](workflow/logs.md) — read logs, grep by
  request_id, body dump, severity filters
- [`workflow/breakpoints.md`](workflow/breakpoints.md) — set
  breakpoints in VS Code, attach mode
- [`workflow/http.md`](workflow/http.md) — Swagger as a debug client,
  inspect bodies
- [`workflow/ws.md`](workflow/ws.md) — Bruno + `make logs-ws`,
  broadcast scenarios

## Quick recipes

| You want to… | Recipe |
|---|---|
| Trace one request end-to-end | Copy `X-Request-ID` from the response → `make logs-web \| grep <id>` |
| See the raw request body | `LOG_HTTP_BODY=1 make up` → trigger → `make logs-web` |
| Pause inside a view | `make up-debug` → set breakpoint → attach VS Code → trigger |
| Watch live WS traffic | `make logs-ws` in one terminal, Bruno WS request in another |
| Debug failing requests only | `make logs-web \| grep WARNING` (4xx) or `\| grep ERROR` (5xx) |
