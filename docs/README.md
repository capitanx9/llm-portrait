# Documentation

Project documentation, organised by audience.

## High-level

- [overview.md](overview.md) — what this project is and what it does.
- [architecture.md](architecture.md) — how the pieces fit together.

## API reference

For someone calling the project from the outside.

- [api/rest/](api/rest/) — REST endpoints (authentication, chat
  rooms, portraits). Generated documentation is served at
  `/api/docs/` when the stack is up.
- [api/ws/](api/ws/) — real-time WebSocket chat. AsyncAPI specification
  + pre-rendered HTML viewer at `/ws/docs/`. Hands-on exploration via
  the Bruno collection at [`../bruno/`](../bruno/).

## Debugging

For someone trying to figure out what the running stack is doing.

- [debug/breakpoints.md](debug/breakpoints.md) — VS Code attach mode
  with debugpy.
- [debug/logging.md](debug/logging.md) — loguru pipeline, request_id
  tracing, access log.
- [debug/http.md](debug/http.md) — Swagger UI as a debugger,
  `LOG_HTTP_BODY=1` body dumps.
- [debug/ws.md](debug/ws.md) — `make ws-demo`, Bruno, reading
  `make logs-ws`.

## Deployment

For someone running the project on a server or laptop.

- [deployment/local.md](deployment/local.md) — local Docker-compose setup.
- [deployment/ec2.md](deployment/ec2.md) — production AWS EC2 deploy.

## Development

For someone contributing to the project.

- [development/workflow.md](development/workflow.md) — branching, PRs,
  conventional commits.
- [development/tooling.md](development/tooling.md) — Poetry, Makefile,
  ruff, mypy, pre-commit.
- [development/testing.md](development/testing.md) — pytest layout,
  what's mocked.
- [development/ci-cd.md](development/ci-cd.md) — GitHub Actions
  pipelines.
