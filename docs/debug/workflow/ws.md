# WebSocket debug workflows

## Drive the WS from a GUI

[`bruno/llm-portrait/ws/chat-room.bru`](../../../bruno/) — real
WebSocket request with four pre-saved messages (valid frame, empty
text, long text, invalid JSON). Open Bruno → activate `local`
environment → run `auth/login.bru` once to populate `{{access_token}}`
→ open `chat-room.bru` → *Connect*.

For broadcast (one user sees the other's messages) open Bruno on a
second machine or as a second window logged in as a different demo
user (e.g. `oleksa` and `mariia` from `make seed-users`). Both
connect to `?token=…` of their respective tokens; the same room name
makes them see each other's frames.

## Pair with the server log

```bash
make logs-ws
```

The same `request_id` is bound at handshake and stays on every
consumer log line for the duration of the connection. `grep` one id
and you get the full lifecycle.

## What to grep

| Looking for | Grep |
|---|---|
| Full lifecycle of one connection | `request_id=<hex>` |
| Handshake details (UA, origin, IP) | the `connect` line — non-handshake frames don't carry these |
| Invalid-JSON frames | `ws invalid json` |
| Disconnect reason | `code=` in the `disconnect` line |

## Sample log session

```
INFO    | app.ws.consumers:connect:46    | request_id=ab12cd34ef56 | room=general user=oleksa client_ip=… user_agent=… origin=… | ws connect accepted
INFO    | app.ws.consumers:receive_json:99 | request_id=ab12cd34ef56 | room=general user=oleksa length=15 frame_type=text message_id=42 | ws message
WARNING | app.ws.consumers:receive:78    | request_id=ab12cd34ef56 | error=… preview=… | ws invalid json
INFO    | app.ws.consumers:disconnect:55 | request_id=ab12cd34ef56 | room=general user=oleksa code=1000 | ws disconnect
```

Two things to notice:

- **Same `request_id` for the entire connection.** The WS middleware
  binds the id once at handshake; every consumer log line picks it
  up via `logger.contextualize`. `grep ab12cd34ef56` gives you the
  full lifecycle of one client.
- **Handshake fields appear only on `connect`.** `client_ip`,
  `user_agent`, `origin` are HTTP-handshake metadata; per-frame
  messages don't have them. Empty values are filtered out, so a bare
  client connecting without those headers simply omits them rather
  than printing `user_agent=None`.

For loguru wiring details see
[`../architecture/loguru.md`](../architecture/loguru.md). Automated
WS coverage lives in `tests/test_chat_ws.py`.
