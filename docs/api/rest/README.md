# REST API

Standard JSON-over-HTTP. Documented as an OpenAPI 3 schema generated
at runtime by [drf-spectacular](https://drf-spectacular.readthedocs.io/),
so the docs are always in sync with the actual views and serializers
— there's no schema file to keep up to date by hand.

## Live documentation

When the stack is up, the schema is reachable at:

- **Swagger UI:** <http://localhost:8000/api/docs/> — interactive,
  with "Try it out" buttons. Click *Authorize* and paste
  `Bearer <access>` to exercise authenticated endpoints.
- **Raw OpenAPI 3 schema:** <http://localhost:8000/api/schema/> — the
  same spec as JSON for tooling that wants to read it directly.

In production the same surface lives at
<https://llm-portrait.gotdns.ch/api/docs/>.

## Authentication

Endpoints under `/api/` require a JWT access token in the
`Authorization` header:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

Get one from `POST /api/auth/login/`. Tokens expire after 15 minutes;
use `POST /api/auth/refresh/` to mint a new access token from the
refresh token. See the Swagger page for the full auth flow.

## GUI client

For repeatable scenarios with auth tokens auto-injected (Login → AI →
Logout), negative-case fixtures, or sharing a flow with someone else,
use the [Bruno collection](../../../bruno/) at the repo root. It
covers the same endpoints Swagger UI does, plus the WebSocket side in
the same collection.

Treat them as complementary — Swagger is the contract (regenerated
from the code at request-time, never out of date), Bruno is the
workflow (curated by hand, has the realistic request bodies and
post-response scripts).

## Where the schema config lives

`SPECTACULAR_SETTINGS` in `src/app/config/settings/base.py`. Project
description, version and the cross-link to the WebSocket docs are set
there.

## AI processing

`POST /api/ai/process/` runs a small LangGraph pipeline on top of the
local Llama. Two actions are supported; both share the same endpoint
and the same response envelope:

- `translate` — translate one message into a target language. Body:
  `{"action": "translate", "message": "...", "target_language": "fr"}`.
  Allowed languages: `ru`, `en`, `uk`, `fr`, `es`, `de`.
- `summarize` — summarize a chat conversation. Body:
  `{"action": "summarize", "conversation": [{"role": "user", "content": "..."}, ...]}`.
  Last 40 turns are kept; older ones are dropped before the prompt.

Successful response (200):

```json
{
  "action": "translate",
  "source_language": "ru",
  "translation": "Hello, how are you?"
}
```

`source_language` is detected by an LLM call before the action runs
(this is the `detect_lang_node` from the brief). `summarize` returns
the summary in that same detected language.

Error responses share the project-wide `{"detail": "..."}` shape:

| Status | When |
|---|---|
| 400 | Validation failed (missing field, unknown action). |
| 401 | No or invalid bearer token. |
| 429 | Rate limit (`LLM_RATE_LIMIT`, default `2/m` per user). |
| 503 | Any node in the pipeline raised — fallback returned. |

The internal pipeline (detect → route → translate / summarize → fallback)
is documented in full in [`docs/langgraph.md`](../../langgraph.md).
