# syntax=docker/dockerfile:1.7

# ==============================================================================
# Builder stage — only builds the .venv. Never reaches the final image.
#
# Why a separate stage:
#   build-essential + libpq-dev are needed to compile psycopg, but useless in
#   prod. They live here, not in runtime. Final image ~250MB instead of ~800.
#
# POETRY_VIRTUALENVS_IN_PROJECT=true — critical:
#   .venv/ ends up at /build/.venv, so a single COPY moves it into runtime.
#
# PYTHONUNBUFFERED=1 — without it `docker logs` lags.
# PYTHONDONTWRITEBYTECODE=1 — keeps .pyc files out of the image.
# PIP_NO_CACHE_DIR=1 — pip won't keep downloaded .whl files; smaller layer.
# POETRY_VERSION=2.3.4 — pin, otherwise builds aren't reproducible.
# POETRY_NO_INTERACTION=1 — otherwise hangs on interactive prompts in CI.
# ==============================================================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=2.3.4 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install "poetry==${POETRY_VERSION}"

WORKDIR /build

# Copy manifests first — Docker caches `poetry install` until they change.
# 99% of edits are Python files, so deps install reuses the cache.
COPY pyproject.toml poetry.lock ./

# --no-root: project is not a package, no need to install it.
# --without dev: ruff/mypy/pytest don't belong in prod (~150MB saved).
RUN poetry install --no-root --without dev


# ==============================================================================
# Runtime stage — minimal prod image. No Poetry, no compilers, no dev deps.
#
# Only .venv from builder is copied here.
#
# libpq5, NOT libpq-dev:
#   libpq-dev is for *compiling* psycopg (lives in builder).
#   libpq5 is for *running* psycopg (lives here).
#   That's the whole point of multi-stage.
#
# useradd --uid 1000 app + USER app:
#   Container runs as non-root. If Django gets exploited — no root inside.
#
# PATH="/app/.venv/bin:$PATH":
#   Lets us call `python`/`gunicorn` without full path.
#   Container-side equivalent of `source .venv/bin/activate`.
# ==============================================================================
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/src

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 app

WORKDIR /app

COPY --from=builder --chown=app:app /build/.venv /app/.venv

COPY --chown=app:app manage.py ./
COPY --chown=app:app src/ ./src/
COPY --chown=app:app docker/entrypoint.dev.sh docker/entrypoint.prod.sh ./
RUN chmod +x ./entrypoint.dev.sh ./entrypoint.prod.sh

# Pre-create staticfiles dir with the right owner so the named volume mount
# inherits ownership from this directory. Otherwise the volume comes up
# owned by root and `collectstatic` fails with PermissionError.
RUN mkdir -p /app/staticfiles && chown -R app:app /app/staticfiles

USER app


# ==============================================================================
# Entrypoint and command
#
# Two entrypoints live in the image; compose picks which to run:
#   docker-compose.dev.yml  → entrypoint.dev.sh  (migrate only)
#   docker-compose.prod.yml → entrypoint.prod.sh (migrate + collectstatic)
#
# `exec "$@"` inside the script replaces the shell so SIGTERM reaches Django.
#
# CMD is the default for `docker run` without compose; compose overrides it:
#   dev  → runserver  (hot-reload)
#   prod → gunicorn   (multi-worker)
# ==============================================================================
ENTRYPOINT ["/app/entrypoint.dev.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


# ==============================================================================
# Builder-dev stage — same as builder but installs dev deps too.
# Used only by the dev image (pytest, ruff, mypy, factory-boy live here).
# ==============================================================================
FROM builder AS builder-dev

RUN poetry install --no-root


# ==============================================================================
# Dev stage — runtime + dev deps. Used by docker-compose.dev.yml.
# Replaces the .venv from runtime with the one that includes dev deps.
# ==============================================================================
FROM runtime AS dev

USER root
COPY --from=builder-dev --chown=app:app /build/.venv /app/.venv
USER app
