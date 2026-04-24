# llm-portrait

Django web application that generates personalized profile descriptions using a local LLM.
Users register, fill in their profile, and generate an AI-written self-description on demand.

## Stack

- Python 3.12, Django 5
- PostgreSQL 16, Redis 7, Celery
- LangChain + Ollama (Llama3.2:3b)
- Docker Compose, Nginx + Gunicorn (production)
- AWS EC2 + ECR, GitHub Actions CI/CD

## Quick start

Requirements: Python 3.12 (recommended via `pyenv`), Poetry.

```bash
make install        # install deps + pre-commit hooks
make check          # run lint + tests
```

The Docker-based workflow (`docker compose up`) is configured in a later stage.

## Development

| Command        | Description                                |
|----------------|--------------------------------------------|
| `make install` | Install dependencies and pre-commit hooks  |
| `make lint`    | Run ruff and mypy                          |
| `make format`  | Auto-format code with ruff                 |
| `make test`    | Run pytest                                 |
| `make check`   | Run lint and tests together                |
| `make clean`   | Remove caches and build artifacts          |
| `make`         | Show all available commands                |

Environment variables are documented in [.env.example](./.env.example).

## Deployment

TBD — see later stages for CI/CD and EC2 deployment setup.
