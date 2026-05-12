# Overview

## What it is

`llm-portrait` is a self-contained backend that serves a small social product: users sign up, join named chat rooms, exchange messages in real time, and offload language-related work — translation, conversation summarization — to a local LLM. Everything is JSON in, JSON out; a separate frontend repo consumes this API.

The backend has two channels with the client:

- **HTTPS (REST)** for everything stateless: authentication, room and message CRUD, AI requests.
- **WSS (WebSocket)** for the chat feed: a client joins one room at a time and receives every message published to it for as long as the connection lives.

The AI side is intentionally a pipeline, not a single prompt. An incoming request first goes through a language-detection node, then routes to either a translation node or a summarization node, with a shared fallback path for any LLM error. Adding a new action means adding a node, not patching a view.

## What the API exposes

- **Auth (`/api/auth/*`)** — register, log in, refresh, log out, current user. JWT pair on login; the refresh token can be blacklisted on logout so it can't be reused.
- **Chat REST (`/api/chat/*`)** — list and create rooms, read paginated message history.
- **Chat WebSocket (`/ws/chat/<room>/`)** — real-time send/receive. JWT is passed as a query-string parameter at handshake; unauthenticated upgrades are rejected.
- **AI processing (`/api/ai/process/`)** — one endpoint, two actions (`translate`, `summarize`). The action chooses the path through the LangGraph; the response shape depends on the action.
- **Health & docs** — `/api/health/`, `/health/` for liveness; `/api/docs/` for the live Swagger UI, `/ws/docs/` for the AsyncAPI viewer.

Five demo users (`oleksa`, `mariia`, `bohdan`, `kateryna`, `taras`) and three demo rooms (`general`, `random`, `ai-help`) are created by `make seed-all`. The same credentials are pre-wired in the Bruno collection and in the Swagger UI examples, so the first authenticated call after a fresh clone is a single click away.

## Stack at a glance

- **Language & web framework** — Python 3.12, Django 5.2, Django REST Framework, drf-spectacular for OpenAPI.
- **Authentication** — `djangorestframework-simplejwt` with token blacklist; 15-min access, 7-day refresh, rotation enabled.
- **Realtime** — Channels + daphne running on a separate `ws` service; Redis as the channel layer for cross-process broadcast.
- **AI pipeline** — LangGraph (detect → translate | summarize → fallback) on top of LangChain; local Ollama serving Llama3.2:3b.
- **Async work** — Celery 5 with Redis broker; Mailhog as the SMTP sink in dev and prod.
- **Data** — PostgreSQL 16, Redis 7 (cache + rate-limit storage + Celery broker + Channels layer).
- **API clients** — Swagger UI at `/api/docs/`, AsyncAPI viewer at `/ws/docs/`, a [Bruno](https://www.usebruno.com/) collection at `bruno/llm-portrait/` covering every endpoint.
- **Containers & runtime** — Docker Compose (`docker-compose.dev.yml`, `docker-compose.prod.yml`), nginx terminating TLS in front of gunicorn (`/`) and daphne (`/ws/`).
- **TLS & domain** — Let's Encrypt via certbot, NoIP DDNS `llm-portrait.gotdns.ch` pointing at an AWS Elastic IP.
- **Hosting** — AWS EC2 (`t3a.large`, Ubuntu 24.04) in `eu-central-1`. Container images in AWS ECR, pushed by CD.
- **CI/CD** — GitHub Actions. CI: ruff, mypy, pytest, AsyncAPI + OpenAPI schema validation. CD: OIDC to AWS → build → push to ECR → SSH into EC2 → recreate stack → four-path smoke test (REST, DRF, ws HTTP, ws upgrade).

## Where to read next

- New to the project? Start with [architecture](./architecture.md) for the service diagram and data flows.
- Want to call the API? See [REST](./api/rest.md) for HTTP endpoints, [WebSocket](./api/ws.md) for the realtime side.
- Want to run it locally? See [local deployment](./deployment/local.md).
- Want to reproduce production? See [EC2 deployment](./deployment/ec2.md).
- Want to debug something? Start with the [debug tour](./debug/README.md).
