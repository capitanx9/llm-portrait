# Local tooling

What runs on the developer's machine, and why.

## Python version pinning

Two files declare the Python version, intentionally:

- **`.python-version`** (read by [pyenv](https://github.com/pyenv/pyenv)). Holds `3.12.10`. When you `cd` into the project, the `python` shim resolves to this version.
- **`requires-python = ">=3.12,<3.13"`** in `pyproject.toml`. Read by Poetry. If the active Python is outside this range, Poetry refuses to install or lock.

Both are needed because they enforce the version at different layers:

- pyenv controls **which `python` runs** when you type the command.
- Poetry controls **which Python's metadata is used to resolve dependencies** and what `.venv` gets bound to.

A common gotcha: Poetry on Mac sometimes picks the system `python3` (Xcode 3.9.x) instead of the pyenv-managed `python` (3.12.x), because `python3` is a separate shim that pyenv doesn't intercept by default. If your `.venv` ends up bound to 3.9, the fix is:

```bash
poetry env remove --all
poetry env use 3.12.10
poetry lock
```

…inside the project directory (so pyenv resolves `python` to 3.12 first).

## Poetry

Dependency manager. Two groups:

- **`[project] dependencies`** — runtime deps (Django, allauth, Celery, LangChain, …). These end up in the production image.
- **`[tool.poetry.group.dev.dependencies]`** — dev-only deps (ruff, mypy, pytest, factory-boy, pre-commit). Excluded from the prod image (`poetry install --without dev` in the builder stage of `docker/Dockerfile`).

Common commands:

```bash
poetry lock         # refresh poetry.lock after editing pyproject.toml
poetry install      # install everything (runtime + dev) into the local .venv
poetry add <pkg>    # add a new runtime dep
poetry add --group dev <pkg>   # add a new dev dep
poetry env info     # which Python is .venv bound to
```

The `.venv` lives in `.venv/` at the project root (forced by `poetry.toml`'s `virtualenvs.in-project = true`). This lets editor / pre-commit pick it up without configuration.

## Makefile structure

The root `Makefile` is just a list of `include` directives. Real targets live in [`makefiles/*.mk`](../../makefiles), one file per domain:

| File          | Purpose                                          |
|---------------|--------------------------------------------------|
| `vars.mk`     | Shared variables (`POETRY`, `SRC`, `TESTS`).     |
| `poetry.mk`   | `install`, `info`, `lock`.                       |
| `lint.mk`     | `lint`, `format`, `mypy` (run on the host).      |
| `test.mk`     | `test`, `test-cov` (run inside the `web` container). |
| `clean.mk`    | `clean` — wipes caches.                          |
| `docker.mk`   | `up`, `down`, `build`, `logs`, `bash`.           |
| `django.mk`   | `migrate`, `makemigrations`, `superuser`, `shell`, `runserver`. |
| `llm.mk`      | `ollama-pull`.                                   |

Each target has a `## comment` after the colon — `make help` parses these and prints them as the command list. Example output:

```
$ make help
Available commands:

  bash            Open a shell in the web container
  build           Rebuild web image
  check           Run lint and tests (use before pushing)
  clean           Remove caches and build artifacts
  ...
```

This pattern keeps targets discoverable and means the README never goes stale on commands — `make help` is always up to date.

The "host vs container" split is intentional:

- Targets that talk to your local Python (`lint`, `format`, `mypy`, `install`, `lock`) call `poetry run …` directly.
- Targets that need the Django runtime (`test`, `migrate`, `superuser`, `shell`) go through `$(COMPOSE) exec web …` so they run inside the container against the actual Postgres / Redis / Ollama services.

## Ruff

Both linter and formatter, replacing flake8 + black + isort.

Configuration in `pyproject.toml`. Notable choices:

- **`line-length = 100`.** Anything wider gets wrapped.
- **`cache-dir = "/tmp/ruff_cache"`.** macOS Docker has a known quirk where bind-mounted directories resist writes from the container's non-root user. Ruff's default cache lives in the project dir, which is bind-mounted, which fails in the container. Pointing the cache at `/tmp` (a writable tmpfs in the container) makes `ruff check` work both on the host and inside `web`.
- **`select = [...]`** — `E`, `W`, `F`, `I`, `N`, `UP`, `B`, `S`, `C4`, `SIM`, `RUF`. Notably no `D` (docstrings) or `ANN` (type annotations) — both would generate noise without giving much for a small project.
- **`ignore`:**
  - `S101` (assert statements) — fine in tests.
  - `RUF012` (mutable class attributes need `ClassVar`) — Django's `Meta` classes use `unique_together = [...]`, `constraints = [...]`, etc. Forcing `ClassVar[list]` everywhere fights the framework.
  - `RUF001` (ambiguous unicode) — we have intentional Cyrillic in `choices` labels (`("magician", "Маг")`).
- **Per-file ignores:**
  - `tests/**/*.py`: ignore `S` (security rules — most fire on test fixtures) and `N802` (non-snake-case function names — pytest test names sometimes use camel case in legacy code).
  - `**/migrations/*.py`: ignore `E501` (long lines), `N806` (non-snake-case in autogenerated `Migration`), `RUF012`.

`make lint` runs `ruff check` + `ruff format --check` + `mypy`. `make format` runs `ruff format` (writes) + `ruff check --fix`.

## Mypy + django-stubs

Static type checking. Strict-ish: `strict = false`, but `warn_unused_ignores` and `warn_redundant_casts` are on, so type-related dead code is caught.

Notable settings:

- **`mypy_path = "src"`** — needed because we use a `src/` layout (`src/app/...`).
- **`ignore_missing_imports = true`** — third-party packages without stubs (langchain, allauth, langchain-ollama, django-ratelimit, …) just become `Any`. Without this flag mypy would scream on every import.
- **`plugins = ["mypy_django_plugin.main"]`** — django-stubs plugin. It teaches mypy about `Manager.objects.filter(...)`, `User.objects.get(...)`, etc.
- **`django_settings_module = "app.config.settings.dev"`** under `[tool.django-stubs]` — the plugin loads this module to learn the project's models.
- **`exclude = ["migrations", ".venv"]`** — generated migration files have all sorts of mypy-unfriendly patterns.

`make mypy` (alias for `poetry run mypy src`) runs only the type check, useful when ruff is already green and you want a faster feedback loop.

## Pre-commit

Configured in `.pre-commit-config.yaml`. Runs on every `git commit`.

Hooks:

- `trailing-whitespace`, `end-of-file-fixer`, `mixed-line-ending` — basic file hygiene.
- `check-yaml`, `check-toml`, `check-merge-conflict`, `check-added-large-files` — sanity checks.
- `ruff` (with `--fix`) — lint + auto-fix.
- `ruff-format` — formatter.

What's intentionally **not** in pre-commit:

- **mypy** — slow on every commit; runs in CI.
- **pytest** — also slow; runs in CI.

The split keeps `git commit` fast (subsecond on a typical change) while still catching style and import issues before they reach CI.

When ruff-format auto-formats a file during the commit, the hook fails the commit and re-stages the file. The next `git commit -m "…"` (with the fixed file) succeeds. This forces you to see the diff ruff applied before it lands.

Install hooks:

```bash
make install   # also runs `poetry install`
# or:
poetry run pre-commit install
```

## Make targets quick reference

```
make help          Show all available commands
make install       Install dependencies and pre-commit hooks
make up            Start the dev stack (web + db + redis + mailhog + ollama + celery)
make down          Stop the dev stack
make build         Rebuild the web image
make logs          Tail compose logs
make bash          Shell into the web container
make migrate       Apply migrations inside the web container
make makemigrations  Generate migrations from model changes
make superuser     Create a Django superuser
make shell         Open a Django shell inside the web container
make ollama-pull   Pull llama3.2:3b into the ollama_data volume
make test          Run pytest inside the web container
make test-cov      Run pytest with coverage report
make lint          Ruff check + ruff format check + mypy
make format        Auto-format with ruff (writes) + ruff --fix
make mypy          Run mypy only
make check         Run lint + test together (use before pushing)
make clean         Remove caches (.pytest_cache, .mypy_cache, .ruff_cache, …)
```
