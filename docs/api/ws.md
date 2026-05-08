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

For the two-user broadcast scenario, see
[`make ws-demo`](../debug/ws.md).

## Channels

| URL | Direction | Message types |
|---|---|---|
| `/ws/chat/<room>/` | client → server | `ChatMessageIn` |
| `/ws/chat/<room>/` | server → client | `ChatMessageOut`, `InvalidJsonError`, `InternalError` |

Full message schemas in [`schemas/asyncapi.yaml`](../../schemas/asyncapi.yaml).
