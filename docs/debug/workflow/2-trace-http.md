# Scenario 2 — Trace an HTTP request by `request_id`

**Goal:** something returned a 4xx / 5xx and you want to see exactly
what the server did. No breakpoints — just logs.

## Trigger and capture the id

In Bruno, send `chat/create-room.bru` with an invalid payload
(empty name). The response is `400 Bad Request`.

Open the response **Headers** tab → copy the value of
`X-Request-ID`, e.g. `ab12cd34ef56`.

## Grep the logs

```bash
make logs-web | grep ab12cd34ef56
```

You see one slice covering the whole request: middleware hops, the
view, any SQL the view ran, the access-log line at the end with
`status=400 duration_ms=12`.

## Severity grep

The access log middleware maps status to log level, so:

```bash
make logs-web | grep WARNING    # every 4xx
make logs-web | grep ERROR      # every 5xx
```

This catches failed requests across all clients without filtering
by id.

## Body dump

If you started with `make up-debug`, the access line already
includes redacted `request_headers`, `request_body`,
`response_headers`, `response_body`. JSON bodies are parsed
structurally; bodies > 4 KB are truncated.

Headers `Authorization`, `Cookie`, `X-Api-Key` and JSON keys
matching `password|token|secret|api_key|access|refresh` are
replaced with `***` before logging. PII in free-text fields
(emails, generated text) is **not** redacted — body dump is dev
only.

If you started with plain `make up`, body dump is off. Restart
with `make up-debug` to turn it on without remembering the env
var.

## What you've used

- Surface 1 (logs): `make logs-web`, severity grep, body dump
- Surface 3 (trigger): Bruno HTTP request
- The bridge: `X-Request-ID` from the response → `grep`
