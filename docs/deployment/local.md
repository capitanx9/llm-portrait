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
- Everything else can stay at defaults — Postgres / Redis / Ollama / Mailhog hostnames are pre-wired to the container names in `docker-compose.dev.yml`.

`REDIS_CACHE_URL` and `REDIS_CHANNELS_URL` are not in `.env.example` and default to `redis://redis:6379/1` and `redis://redis:6379/2` in [`base.py`](../../src/app/config/settings/base.py). Add an explicit override only if you want to point cache or the Channels layer at a different db.

## 2. Build the image

```bash
make build
```

This rebuilds the project image (shared by `web`, `ws`, and `celery`). The first build pulls Python 3.12 and installs all dependencies through Poetry — expect 2–3 minutes.

## 3. Start the stack

```bash
make up
```

This brings up seven containers:

| service   | image                        | port (host) |
|-----------|------------------------------|-------------|
| `web`     | `llm-portrait-web:latest`    | 8000        |
| `ws`      | `llm-portrait-web:latest`    | 8001        |
| `celery`  | `llm-portrait-web:latest`    | —           |
| `db`      | `postgres:16-alpine`         | —           |
| `redis`   | `redis:7-alpine`             | —           |
| `mailhog` | `mailhog/mailhog:latest`     | 8025 (UI)   |
| `ollama`  | `ollama/ollama:latest`       | —           |

`web`, `ws`, and `celery` are the same image with different commands. Migrations are applied automatically on `web` startup via the entrypoint.

## 4. First-run setup

Run these once after `make up`:

```bash
make superuser     # Create a Django admin user (optional, for /admin/)
make ollama-pull   # Pull llama3.2:3b into the ollama_data volume (~2 GB, 5 min)
make seed-all      # 5 demo users + 3 demo rooms + 54 demo messages
```

The model download is one-time — the volume `ollama_data` survives container restarts. `make seed-all` is idempotent; re-run it any time you want a clean demo state.

## 5. Open the app

- REST API: <http://localhost:8000/api/>
- Swagger UI: <http://localhost:8000/api/docs/>
- AsyncAPI viewer: <http://localhost:8000/ws/docs/>
- Django admin: <http://localhost:8000/admin/>
- Mailhog UI (incoming emails): <http://localhost:8025>

A typical smoke test (with the Bruno collection at [`bruno/llm-portrait/`](../../bruno/llm-portrait/)):

1. Open the collection in Bruno, activate the `local` environment, run `auth/login.bru` — the post-response script stashes `{{access_token}}` and `{{refresh_token}}`. Default creds (`oleksa` / `pass1234`) come from `make seed-users`.
2. Run `chat/list-rooms.bru` → see `general`, `random`, `ai-help`.
3. Run `chat/get-room-messages.bru` for `general` → see 18 seeded messages.
4. Open `ws/chat-room.bru` → Connect → you're in the room. Send `{"text": "hello"}` → see it echo back via group_send.
5. Run `ai/translate-ru-en.bru` → wait 1–30s (Ollama warmth) → see the English translation.

## Common make targets

| Target              | What it does                                            |
|---------------------|---------------------------------------------------------|
| `make up`           | Start the dev stack                                     |
| `make up-debug`     | Same, but with `DEBUGPY=1` + `LOG_HTTP_BODY=1`          |
| `make down`         | Stop the stack                                          |
| `make build`        | Rebuild the project image                               |
| `make logs-<svc>`   | Follow logs from one service (`web`, `ws`, `celery`, …) |
| `make bash`         | Shell into the `web` container                          |
| `make migrate`      | Run `manage.py migrate`                                 |
| `make seed-all`     | Seed demo users + rooms + messages                      |
| `make flush-demo`   | Remove all seeded users / rooms / messages              |
| `make superuser`    | Run `manage.py createsuperuser`                         |
| `make shell`        | Open `manage.py shell` inside `web`                     |
| `make test`         | Run pytest inside `web`                                 |
| `make openapi-build`| Regenerate `schemas/openapi.yaml`                       |
| `make ollama-pull`  | `ollama pull llama3.2:3b` inside `ollama`               |
| `make lint`         | ruff check + ruff format check + mypy                   |
| `make format`       | Auto-format with ruff                                   |
| `make clean`        | Remove `.pytest_cache`, `.mypy_cache`, etc.             |

`make help` lists the full grouped index.

## Troubleshooting

**Port 8000 / 8001 / 8025 already in use.** Either `make down` to stop the project, or change the port mapping in `docker-compose.dev.yml`.

**LLM endpoint returns "model 'llama3.2:3b' not found".** You forgot `make ollama-pull`. Run it once and the volume keeps the model.

**Tests fail with `Redis ConnectionError: Error -3 connecting to redis:6379`.** Tests require Redis (used by django-cache and django-ratelimit). Make sure `make up` is running first — `make test` doesn't bring services up on its own.

**Pre-commit hook fails with `No module named pre_commit`.** The hook calls Python from your local Poetry venv. Run `poetry install` once on the host to populate the venv with dev deps (ruff, pytest, factory-boy, pre-commit, …).

**Ruff format keeps "fixing" the same file in pre-commit.** Run `make format` once to apply pending changes, then commit again — the hook auto-formats and re-stages (which forces you to recommit so you can review the diff).

**Mac Docker volume permission errors with `.ruff_cache`.** Already handled — `pyproject.toml` overrides `cache-dir = "/tmp/ruff_cache"` so ruff writes to the writable tmpfs instead of a bind-mount on macOS.

**AI endpoint hangs on the first request.** Cold Ollama loads the model into RAM on the first call after idle — 30–60s on a laptop CPU. Subsequent calls are 1–10s. The dev `web` runs `runserver` which has no request timeout, so just wait. On EC2, the chain is gunicorn (`--timeout 600`) → nginx (`proxy_read_timeout 600s`) → Ollama.
