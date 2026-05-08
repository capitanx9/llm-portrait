# Logging architecture

Single sink: [loguru](https://loguru.readthedocs.io/). Stdlib `logging`
is intercepted at root and rerouted, so Django, DRF, Channels, Celery,
gunicorn and daphne all share the same output.

## Wiring

- Bootstrap: `src/app/config/logging.py`, called from every entry
  point (`manage.py`, `wsgi.py`, `asgi.py`, `celery.py`)
- Stdlib intercept: `InterceptHandler` installed at the root logger
- Django framework loggers (`django`, `daphne`, `channels`,
  `daphne.management.commands.runserver`, `django.request`,
  `django.channels.server`) have their own `StreamHandler` neutralised
  in `LOGGING` so access lines don't print twice
- HTTP request id: `app.core.middleware.RequestIdMiddleware`
- WS request id: `app.ws.middleware.RequestIdMiddleware`
- Access log: `app.core.middleware.HttpAccessLogMiddleware`

## Configuration

| Env var | Default | Effect |
|---|---|---|
| `LOG_FORMAT` | `human` | `human` colored or `json` for log shippers |
| `LOG_LEVEL` | `INFO` | `DEBUG` for SQL queries and framework noise |
| `LOG_HTTP_BODY` | unset | `1` enables request/response body dump on the access log (dev only) |

## Format

`human` — one colored line per record. Bound fields render as
`key=value`:

```
INFO | app.ws.consumers:receive_json:99 | request_id=ab12cd34ef56 | room=general user=oleksa length=15 | ws message
```

`json` — one JSON object per record. Bound fields become top-level
keys; suitable for CloudWatch / Loki / Promtail without a custom
parser.

## Request id

Every HTTP request and WebSocket connection gets a 12-char
`request_id` that:

- is bound by middleware via `logger.contextualize(request_id=...)`
- appears on every log line within that scope
- is echoed back as the `X-Request-ID` response header (HTTP)
- is read from an incoming `X-Request-ID` header if the caller
  provided one

Grep one id and you see the full lifecycle: handshake → middleware →
view → SQL → response.

## Access log

`HttpAccessLogMiddleware` writes one structured line per HTTP request
with `method`, `path`, `status`, `duration_ms`, `user_id`,
`view_name`, `client_ip`, `request_id`. Severity follows status:

| Status | Level |
|---|---|
| 2xx / 3xx | INFO |
| 4xx | WARNING |
| 5xx | ERROR |

## Body dump (dev only)

`LOG_HTTP_BODY=1` adds `request_headers`, `request_body`,
`response_headers`, `response_body` to the access line. JSON bodies
are parsed structurally; other content types report a one-line
summary (`<multipart/form-data, 12345 bytes>`). Bodies > 4 KB are
truncated.

Two redaction layers run before logging:

- Headers `Authorization`, `Cookie`, `Set-Cookie`, `X-Api-Key`,
  `Proxy-Authorization`, `X-Auth-Token` → values replaced with `***`
- JSON keys whose name contains `password`, `token`, `secret`,
  `api_key`, `access`, `refresh` → values replaced with `***`

Production stance: structured access lines are always on, body dumps
are off. Redaction is a substring match, not a guarantee, and PII in
free-text fields (emails, usernames, generated text) wouldn't be
caught.
