# Local deployment

A step-by-step from a fresh machine to a fully working dev stack with the LLM enabled.

## Prerequisites

- **Docker Desktop** (Mac / Windows) or `docker` + `docker-compose-plugin` (Linux). Everything actually runs in containers.
- **Python 3.12** via [pyenv](https://github.com/pyenv/pyenv). Local Python is needed only for two things:
  - regenerating `poetry.lock` when dependencies change,
  - running the pre-commit hook.
  Day-to-day work happens inside the `web` container, so you don't need to install project deps locally.
- **[Poetry](https://python-poetry.org)**, version 2.x (the project uses `poetry-core>=2.0.0`).

The repo pins the Python version through `.python-version` (read by pyenv) and `requires-python = ">=3.12,<3.13"` in `pyproject.toml`. As long as pyenv resolves `python` to 3.12.x in this directory, Poetry will pick it up.

## 1. Clone and configure env

```bash
git clone git@github.com:capitanx9/llm-portrait.git
cd llm-portrait

cp .env.example .env
```

Open `.env` in an editor and fill in:

- `SECRET_KEY` — any random string for dev (e.g. `python -c "import secrets; print(secrets.token_urlsafe(50))"`).
- `GITHUB_OAUTH_CLIENT_ID` / `GITHUB_OAUTH_CLIENT_SECRET` — only if you want to test the GitHub OAuth flow locally. See `development/workflow.md` for how to register an OAuth App; otherwise leave empty and the GitHub button will simply 500 if clicked.
- Everything else can stay at defaults — Postgres / Redis / Ollama / Mailhog hostnames are pre-wired to the container names in `docker-compose.dev.yml`.

`REDIS_CACHE_URL` is not in `.env.example` and defaults to `redis://redis:6379/1` in [`base.py`](../../src/app/config/settings/base.py). Add an explicit override only if you want to point cache at a different db.

## 2. Build the image

```bash
make build
```

This rebuilds only the `web` image. The first build pulls Python 3.12 and installs all dependencies through Poetry — expect 2–3 minutes.

## 3. Start the stack

```bash
make up
```

This brings up six containers:

| service   | image                       | port (host) |
|-----------|-----------------------------|-------------|
| `web`     | `llm-portrait-web:latest`   | 8000        |
| `db`      | `postgres:16-alpine`        | —           |
| `redis`   | `redis:7-alpine`            | —           |
| `mailhog` | `mailhog/mailhog:latest`    | 8025 (UI)   |
| `ollama`  | `ollama/ollama:latest`      | —           |
| `celery`  | `llm-portrait-celery:latest` | —          |

Migrations are applied automatically on `web` startup via the entrypoint.

## 4. First-run setup

Run these once after `make up`:

```bash
make superuser     # Create a Django admin user
make ollama-pull   # Pull llama3.2:3b into the ollama_data volume (~2 GB, 5 min)
```

The model download is one-time — the volume `ollama_data` survives container restarts.

## 5. Open the app

- Main app: <http://localhost:8000>
- Mailhog UI (incoming emails): <http://localhost:8025>
- Django admin: <http://localhost:8000/admin>

A typical smoke test:

1. Sign up at `/accounts/signup/` with `bob@example.com` / `pass1234`.
2. Open Mailhog → see the welcome email.
3. Fill the tarot fields on `/portrait/` and click Save.
4. Click "Сгенерировать портрет" → wait 30–90s → see the description appear.

## Common make targets

| Target              | What it does                                           |
|---------------------|--------------------------------------------------------|
| `make up`           | Build (if needed) and start the dev stack              |
| `make down`         | Stop the stack (containers and network removed)        |
| `make build`        | Rebuild the `web` image                                |
| `make logs`         | Follow logs from all services                          |
| `make bash`         | Shell into the `web` container                         |
| `make migrate`      | Run `manage.py migrate`                                |
| `make makemigrations` | Run `manage.py makemigrations`                       |
| `make superuser`    | Run `manage.py createsuperuser`                        |
| `make shell`        | Open `manage.py shell` inside `web`                    |
| `make test`         | Run pytest inside `web`                                |
| `make test-cov`     | Run pytest with coverage report                        |
| `make ollama-pull`  | `ollama pull llama3.2:3b` inside the `ollama` container |
| `make lint`         | Run ruff check + ruff format check + mypy              |
| `make format`       | Auto-format with ruff and apply safe lint fixes        |
| `make clean`        | Remove `.pytest_cache`, `.mypy_cache`, etc.            |

`make help` lists everything.

## Troubleshooting

**Port 8000 / 8025 already in use.** Either `make down` to stop the project, or change the port mapping in `docker-compose.dev.yml`.

**LLM endpoint returns "model 'llama3.2:3b' not found".** You forgot `make ollama-pull`. Run it once and the volume keeps the model.

**Tests fail with `Redis ConnectionError: Error -3 connecting to redis:6379`.** Tests require Redis (used by django-cache and django-ratelimit). Make sure `make up` is running first — `make test` doesn't bring services up on its own.

**Profile data doesn't reflect what you just saved in tests.** Django caches related-object lookups on the user instance. After `profile.save()`, call `user.refresh_from_db()` before reading `user.profile.<field>`. The same gotcha hit our own tests in [`tests/test_llm.py`](../../tests/test_llm.py).

**Pre-commit hook fails with `No module named pre_commit`.** The hook calls Python from your local Poetry venv. Run `poetry install` once on the host to populate the venv with dev deps (ruff, pytest, factory-boy, pre-commit, …).

**Ruff format keeps "fixing" the same file in pre-commit.** Run `make format` once to apply pending changes, then commit again — the hook is set up to auto-format and re-stage (which forces you to recommit so you can review the diff).

**Mac Docker volume permission errors with `.ruff_cache`.** Already handled — `pyproject.toml` overrides `cache-dir = "/tmp/ruff_cache"` so ruff writes to the writable tmpfs instead of a bind-mount on macOS.

**LLM generation hangs / timeouts.** On a laptop CPU one generation takes 30–90 seconds. The dev `web` runs `runserver`, which has no request timeout, so just wait. On EC2, see [ec2.md](./ec2.md) for the gunicorn / nginx / Ollama timeout chain.
