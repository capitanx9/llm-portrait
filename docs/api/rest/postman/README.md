# Postman collection (REST)

Hands-on Postman artefact for the REST API.

## Why we ship one

REST endpoints are also reachable via Swagger UI at `/api/docs/` (see
[`../README.md`](../README.md) — "Why no Postman collection for REST"
section). The AI processing endpoint added in PR-6 is the first one
that's awkward to drive from Swagger because the request bodies are
nested (`conversation: [{role, content}, ...]`) and you'll often want
to repeat the same call many times. A pre-baked Postman collection
makes that loop cheap.

The collection covers:

- `POST /api/auth/register/` — create the demo user (idempotent — 400
  on re-run if already exists).
- `POST /api/auth/login/` — grabs `access` and writes it into the
  collection variable `access_token` via a post-response script.
- `GET /api/auth/me/` — quick whoami.
- `POST /api/ai/process/` — six requests covering translate (ru → en,
  en → fr), summarize, and the three error paths (400 missing field,
  400 unknown action, 401 no token).

## How to import

1. **File → Import → drop**
   `llm-portrait-rest.postman_collection.json`. The collection appears
   in your sidebar.
2. **Import an environment** from the WS folder —
   [`../../ws/postman/llm-portrait-local.postman_environment.json`](../../ws/postman/llm-portrait-local.postman_environment.json)
   for the local stack, or `…-prod.postman_environment.json` for the
   deployed instance. The `base_http` variable is what this REST
   collection uses; the `base_ws` one is unused here but harmless.
3. **Activate the environment** via the dropdown in the top right.
4. **Run order:** `Register (one-time)` → `Login (get JWT)` → any AI
   request. The Login script auto-injects the token; you don't have
   to paste it anywhere.

## Why the environment lives next to WS, not REST

Both APIs share the same backend host. Duplicating the `base_http` env
across two folders means a host change has to land in two places.
Single source of truth wins; the REST collection just points at the
WS folder for the env file.

## Known issues

None for REST — Postman's collection v2.1 schema has first-class
fields for HTTP requests. The "WebSocket request demotes to HTTP GET
on import" bug only affects the WS collection.
