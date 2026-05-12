# llm-portrait

Django backend for a real-time chat with an AI side-channel: users register, log in, join named rooms, exchange messages over WebSocket, and dispatch translation or summarization requests to a local LLM via a LangGraph pipeline.

Production deploy: <https://llm-portrait.gotdns.ch>

REST API browser: <https://llm-portrait.gotdns.ch/api/docs/> · WebSocket spec: <https://llm-portrait.gotdns.ch/ws/docs/>

**Stack:**

- **Language & web framework** — Python 3.12, Django 5.2, Django REST Framework
- **Realtime** — Channels + daphne (WebSocket), Redis as channel layer
- **Auth & API contract** — simplejwt (JWT + blacklist), drf-spectacular (OpenAPI)
- **AI** — LangGraph + LangChain, Ollama (Llama3.2:3b)
- **Async work** — Celery + Redis broker
- **Data** — PostgreSQL 16, Redis 7 (cache + broker + channels)
- **Runtime & deploy** — Docker Compose, Nginx + gunicorn, AWS EC2 + ECR, GitHub Actions

## Documentation

The full documentation lives under [`docs/`](./docs/):

- [Overview](./docs/overview.md) — what the project is and what users can do.
- [Architecture](./docs/architecture.md) — services, diagrams, data flow.
- API: [REST](./docs/api/rest.md), [WebSocket](./docs/api/ws.md).
- Debugging: [tour](./docs/debug/README.md) of logs, debugpy, and clients.
- Deployment: [local](./docs/deployment/local.md), [AWS EC2](./docs/deployment/ec2.md).
- Development: [workflow](./docs/development/workflow.md), [tooling](./docs/development/tooling.md), [testing](./docs/development/testing.md), [CI/CD](./docs/development/ci-cd.md).
