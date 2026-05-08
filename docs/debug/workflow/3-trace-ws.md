# Scenario 3 — Same workflow for WebSocket

**Goal:** trace a WS connection end-to-end. The recipe is identical
to Scenario 2 except for *where you read `request_id`*.

## The asymmetry

WebSocket clients (Bruno, browsers, websocat) don't expose
upgrade-response headers. `X-Request-ID` is set on the handshake
response, but Bruno's UI doesn't show it. So you read the id from
the **server log** instead.

Everything else — grepping, severity, breakpoints — is the same as
HTTP.

## Trigger and capture the id

Terminal 1:

```bash
make logs-ws
```

In Bruno, open `ws/chat-room.bru` → **Connect**. Terminal 1 prints
something like:

```
INFO | app.ws.consumers:connect:46 | request_id=ef99aa11bb22 | room=general user=oleksa client_ip=… | ws connect accepted
```

Copy the `request_id`.

## Grep the lifecycle

```bash
make logs-ws | grep ef99aa11bb22
```

The same id is bound at handshake and stays on every consumer log
line: every received frame, every broadcast, the disconnect line
with the close code. One grep = full lifecycle of one client.

## Useful greps

```bash
make logs-ws | grep "request_id=ef99aa11bb22"   # full lifecycle of one connection
make logs-ws | grep "ws connect accepted"       # all handshakes (with UA, origin, client_ip)
make logs-ws | grep "ws invalid json"           # frames the consumer rejected as malformed
make logs-ws | grep "ws disconnect"             # disconnect lines, including close codes
```

Handshake fields (`client_ip`, `user_agent`, `origin`) appear
**only** on `ws connect accepted` lines, because they're
HTTP-handshake metadata — subsequent frame logs don't carry them.
So if you need to correlate a UA with the rest of a session, grep
the connect line first to find the `request_id`, then grep that id
to get the rest.

## Breakpoints in consumers

`make up-debug` covers WS too — daphne runs inside the `ws`
container with `DEBUGPY=1`. Set a breakpoint in
`src/app/ws/consumers.py`, attach VS Code (the same launch
configuration works), connect from Bruno, the breakpoint hits.

## Broadcast scenarios

To see one user receive another's messages: open Bruno in two
windows, log in as different demo users (e.g. `oleksa` and
`mariia`), connect both to the same room. Each frame triggers a
broadcast that the other window receives. Both connections share
the same room but have **different `request_id`s** — one per
connection, not per room.

## What you've used

- Surface 1 (logs): `make logs-ws`, `request_id` discovery from
  the `connect` line
- Surface 3 (trigger): Bruno WS request
- Surface 2 (optional): `make up-debug` + breakpoint in consumer
