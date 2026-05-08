# HTTP debug workflows

## Swagger UI as a one-off client

Swagger at `http://localhost:8000/api/docs/` is a thin HTTP client
with the auth flow pre-wired:

1. Hit `POST /api/auth/login/` from inside Swagger to get a JWT
2. Click *Authorize*, paste `Bearer <access>`
3. Every subsequent operation runs as that user

Pair with a [breakpoint](breakpoints.md) in the view and *Execute*
in Swagger — the fastest way to inspect a single live request.

For repeatable scenarios use Bruno —
[`../../api/rest.md`](../../api/rest.md).

## Inspect request and response bodies

```bash
LOG_HTTP_BODY=1 make up
make logs-web
# trigger via Swagger / Bruno / curl
```

The access line gains `request_headers`, `request_body`,
`response_headers`, `response_body`. Sensitive fields are redacted —
see [`../architecture/loguru.md`](../architecture/loguru.md).

Turn it off:

```bash
make down && make up
```

## Pair the request with the server log

Every Swagger / Bruno / curl response carries an `X-Request-ID`
header. Copy it, then:

```bash
make logs-web | grep <request-id>
```

You get the access line, view body, SQL, and response in one stream.

## When to use what

| Question | Tool |
|---|---|
| Try one endpoint with auth | Swagger UI |
| Repeat a flow with auto-token wiring | Bruno |
| See what hit the server | `LOG_HTTP_BODY=1` + `make logs-web` |
| Pause inside the view | [breakpoints](breakpoints.md) |
