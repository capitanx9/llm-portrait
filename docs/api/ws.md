# WebSocket API

Real-time chat over WebSocket. Local: `ws://localhost:8001/ws/`.
Production: `wss://llm-portrait.gotdns.ch/ws/`.

## Specification

- Format: AsyncAPI 3.1
- Source: [`schemas/asyncapi.yaml`](../../schemas/asyncapi.yaml)
- Viewer: AsyncAPI HTML at `/ws/docs/`
- Raw schema: [`schemas/asyncapi.yaml`](../../schemas/asyncapi.yaml)

The viewer is pre-rendered offline by `make asyncapi-build` and served
as a static file. CI runs `make asyncapi-validate` on every PR.

## Origin validation

The ASGI stack wraps the WebSocket router in Channels'
[`OriginValidator`](https://channels.readthedocs.io/en/latest/topics/security.html#websocket-origin-validation),
which whitelists handshakes by the `Origin` header (scheme + host +
port). The allow-list is `WS_ALLOWED_ORIGINS` in `.env` —
comma-separated, same shape as `CORS_ALLOWED_ORIGINS`. Dev defaults
to `http://localhost:5173,http://127.0.0.1:5173` (Vite's default).
Handshakes from an origin outside the list are refused with HTTP
403 before any auth runs.

## Authentication

JWT access token in the query string on the upgrade URL:

```
wss://host/ws/chat/<room>/?token=<access>
```

Tokens are issued by the REST `POST /api/auth/login/` endpoint —
see [`rest.md`](rest.md). Browsers can't set custom headers on
`WebSocket(...)` constructors, so the query string is the documented
place.

## GUI client

[`bruno/llm-portrait/ws/chat-room.bru`](../../bruno/) — real WebSocket
request with four pre-saved messages (valid frame, empty text, long
text, invalid JSON). The login script populates `{{access_token}}`
automatically.

For broadcast, open Bruno in two windows logged in as different
demo users (e.g. `oleksa` and `mariia` from `make seed-users`). For
debug workflow see [`../debug/workflow/3-trace-ws.md`](../debug/workflow/3-trace-ws.md).

## Channels

| URL | Direction | Message types |
|---|---|---|
| `/ws/chat/<room>/` | client → server | `ChatMessageIn` |
| `/ws/chat/<room>/` | server → client | `ChatMessageOut`, `InvalidJsonError`, `InternalError` |

Full message schemas in [`schemas/asyncapi.yaml`](../../schemas/asyncapi.yaml).
