# REST API

JSON over HTTP. Local: `http://localhost:8000/api/`. Production:
`https://llm-portrait.gotdns.ch/api/`.

## Specification

- Format: OpenAPI 3
- Source: Django views + serializers, annotated with
  [drf-spectacular](https://drf-spectacular.readthedocs.io/)
- Viewer: Swagger UI at `/api/docs/` (live, generated per request)
- Raw schema (live): `/api/schema/`
- Raw schema (file): [`schemas/openapi.yaml`](../../schemas/openapi.yaml)
  — committed for the frontend's `openapi-typescript` codegen

`make openapi-build` regenerates the file. CI fails the build if the
committed file is out of sync with what the code produces, so the
frontend never reads a stale schema.

## Authentication

JWT bearer token in the `Authorization` header:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

- Issued by `POST /api/auth/login/`
- Rotated by `POST /api/auth/refresh/`
- Blacklisted by `POST /api/auth/logout/`
- Access token TTL: 15 minutes; refresh token TTL: 7 days

## Rate limits

| Endpoint | Limit | Setting |
|---|---|---|
| `POST /api/ai/process/` | `LLM_RATE_LIMIT` per user (default `2/m`) | `src/app/config/settings/base.py` |

Backed by Redis via `django-ratelimit`. 429 response shape:
`{"detail": "Too many requests."}`.

## GUI client

[`bruno/llm-portrait/`](../../bruno/) — covers every endpoint plus
the WebSocket side in one collection. The login script auto-injects
`access_token` and `refresh_token` into collection variables.

## Endpoints

| Path | Method | Purpose |
|---|---|---|
| `/api/auth/register/` | POST | Create a user |
| `/api/auth/login/` | POST | Issue access + refresh tokens |
| `/api/auth/refresh/` | POST | Rotate access token |
| `/api/auth/logout/` | POST | Blacklist refresh token |
| `/api/auth/me/` | GET | Current user |
| `/api/chat/rooms/` | GET, POST | List or create rooms |
| `/api/chat/rooms/<name>/messages/` | GET | Paginated room history |
| `/api/ai/process/` | POST | Translate or summarize via LangGraph |
| `/api/health/` | GET | Liveness probe |

Full request/response shapes in Swagger UI.

## AI processing

`POST /api/ai/process/` dispatches on the `action` field.

**Translate** — `{"action": "translate", "message": "...", "target_language": "fr"}`.
Allowed languages: `ru`, `en`, `uk`, `fr`, `es`, `de`.

**Summarize** — `{"action": "summarize", "conversation": [{"role": "...", "content": "..."}, ...]}`.
Last 40 turns are kept; older turns are dropped.

**Response (200):**

```json
{
  "action": "translate",
  "source_language": "ru",
  "translation": "Hello, how are you?"
}
```

`source_language` is detected by an LLM call before the action runs.
`summarize` returns the summary in that same detected language.

**Error responses** all use `{"detail": "..."}`:

| Status | When |
|---|---|
| 400 | Validation failed (missing field, unknown action) |
| 401 | No or invalid bearer token |
| 429 | Rate limit |
| 503 | An LLM node raised — fallback returned |
