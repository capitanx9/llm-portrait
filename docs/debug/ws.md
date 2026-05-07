# Debugging WebSocket connections

Two complementary tools:

- **`make ws-demo`** — a CLI helper that prints two ready-to-paste
  `websocat` invocations for two demo users. Fastest way to eyeball a
  live two-user chat scenario in the terminal.
- **Postman collection** in [`../api/ws/postman/`](../api/ws/postman/)
  — GUI client with auth, query parameters and message templates
  pre-configured. Best when you want to repeat the same scenario or
  share it with someone else.

For the other debug surfaces, see:

- [`breakpoints.md`](breakpoints.md) — VS Code attach mode, debugpy
- [`logging.md`](logging.md) — loguru, request_id, access log
- [`http.md`](http.md) — Swagger UI as a debugging tool

## Using `make ws-demo`

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

## Using the Postman collection

> *Coming soon — the collection lives at
> `docs/api/ws/postman/llm-portrait-ws.postman_collection.json` once
> it's exported from Postman GUI. See
> [`../api/ws/README.md`](../api/ws/README.md) for what's inside.*

Pair the collection with `make logs-ws` in a terminal. The same
`request_id` will appear in both the response payload (via the
`X-Request-ID`-style log line) and in your `make logs-ws` output, so
a single id stitches the GUI activity to the server-side stream.

## Reading `make logs-ws`

A typical session for one connection looks like this in
`LOG_FORMAT=human`:

```
INFO  | app.ws.consumers:connect:46 | request_id=ab12cd34ef56 | room=ws-debug user=wsuser client_ip=151.101.128.223 user_agent=... origin=... | ws connect accepted
INFO  | app.ws.consumers:receive_json:99 | request_id=ab12cd34ef56 | room=ws-debug user=wsuser length=15 frame_type=text message_id=42 | ws message
WARNING | app.ws.consumers:receive:78 | request_id=ab12cd34ef56 | error=... preview=... | ws invalid json
INFO  | app.ws.consumers:disconnect:55 | request_id=ab12cd34ef56 | room=ws-debug user=wsuser code=1000 | ws disconnect
```

Two things to notice:

- **Same `request_id` for the entire connection.** The WS middleware
  binds the id once at handshake; every consumer log line picks it up
  via `logger.contextualize`. `grep ab12cd34ef56` gives you the full
  lifecycle of one client.
- **Handshake fields appear only on `connect`.** `client_ip`,
  `user_agent`, `origin` are HTTP-handshake metadata — they don't
  exist on per-frame messages. Empty values are filtered out, so a
  bare `websocat` connection without `-H` will simply omit them
  instead of printing `user_agent=None`.

For details about how request_id works, see [`logging.md`](logging.md).
