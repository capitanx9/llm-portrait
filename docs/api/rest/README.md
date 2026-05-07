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

## Why no Postman collection for REST

Swagger UI's *Try it out* mode already covers what a Postman REST
collection would: an authenticated GUI client backed by a schema. The
schema is generated from the code at runtime, so a hand-maintained
Postman export would lag behind every endpoint change. We keep
hand-maintained client artefacts only where there's no alternative —
for the WebSocket side, see [`../ws/`](../ws/).

## Where the schema config lives

`SPECTACULAR_SETTINGS` in `src/app/config/settings/base.py`. Project
description, version and the cross-link to the WebSocket docs are set
there.
