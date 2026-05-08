# Reading logs

For loguru wiring details see
[`../architecture/loguru.md`](../architecture/loguru.md).

## Tail by service

| Command | Service |
|---|---|
| `make logs-web` | gunicorn / Django |
| `make logs-ws` | daphne / Channels |
| `make logs-celery` | Celery worker |
| `make logs-db` | Postgres |
| `make logs-redis` | Redis |
| `make logs-mailhog` | Mailhog |
| `make logs-ollama` | Ollama |

`make logs` tails everything at once — noisy, prefer the per-service
shortcuts.

## Grep by request_id

Every log line within a request scope carries `request_id=<hex>`. The
id is also returned as the `X-Request-ID` response header, so you
can copy it from the client's response.

```bash
make logs-web | grep ab12cd34ef56
```

That single grep gives you the access-log line, every middleware
hop, the view body, SQL queries, downstream calls (Celery, Ollama,
SMTP) and the response.

## Inspect request and response bodies

```bash
LOG_HTTP_BODY=1 make up
make logs-web
# trigger the request via Bruno / Swagger / curl
make down && make up   # turn body dump back off
```

Each access line gains `request_headers`, `request_body`,
`response_headers`, `response_body`. JSON is structured; other
content types are summarised. Sensitive fields are redacted (see
`../architecture/loguru.md`).

## Switch format for log shippers

```bash
LOG_FORMAT=json make up
```

Top-level JSON keys for every bound field — pipe through `jq` or feed
into CloudWatch / Loki without a custom parser.

## Severity filter

```bash
make logs-web | grep WARNING   # every 4xx
make logs-web | grep ERROR     # every 5xx
```

The access log middleware maps status to severity, so these greps
already capture failed requests without further filters.
