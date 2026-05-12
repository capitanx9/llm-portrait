# Documentation

Project documentation, organised by audience.

## High-level

- [overview.md](overview.md) — what this project is and what it does.
- [architecture.md](architecture.md) — how the pieces fit together.

## API reference

For someone calling the project from the outside.

- [api/rest.md](api/rest.md) — REST endpoints (authentication, chat
  rooms, AI processing). Live schema served at `/api/docs/`; the same
  schema is committed at [`schemas/openapi.yaml`](../schemas/openapi.yaml)
  for downstream codegen.
- [api/ws.md](api/ws.md) — real-time WebSocket chat. AsyncAPI spec at
  [`schemas/asyncapi.yaml`](../schemas/asyncapi.yaml), pre-rendered
  HTML viewer at `/ws/docs/`.
- Hands-on exploration for both: the Bruno collection at
  [`../bruno/`](../bruno/).

## Debugging

For someone trying to figure out what the running stack is doing.
See [debug/README.md](debug/README.md) for the overview; the
[workflow/](debug/workflow/) folder contains five numbered scenarios
(setup → breakpoint → trace HTTP → trace WS → service map).

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
