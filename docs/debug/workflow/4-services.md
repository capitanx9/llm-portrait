# Scenario 4 — Which service log to read

**Goal:** map a symptom to the right `logs-<service>` command.
Scenarios 2 and 3 covered `logs-web` and `logs-ws`. This file
covers the rest.

`make logs` tails everything at once — useful when you don't yet
know which process is misbehaving, but noisy. Once you have a
hypothesis, switch to a specific service.

## logs-celery — background tasks

**When:** an endpoint returned `202 Accepted` but no result
appears, AI processing hangs, scheduled jobs don't run.

```bash
make logs-celery | grep "ai_process_start"   # task entered
make logs-celery | grep "ai_node_failed"     # LangGraph node raised
make logs-celery | grep ERROR                # any task crash
```

Celery tasks inherit `request_id` from the HTTP request that
enqueued them, so you can trace an AI call from the REST endpoint
straight into the worker:

```bash
make logs-web    | grep ab12cd34ef56   # the POST /api/ai/ that started it
make logs-celery | grep ab12cd34ef56   # the task that picked it up
```

## logs-db — Postgres

**When:** migration fails, query is slow, a constraint violation
shows up as 500 in `logs-web` but the cause is unclear.

```bash
make logs-db | grep ERROR              # constraint violations, syntax errors
make logs-db | grep "duration:"        # slow-query log (if log_min_duration_statement is set)
```

For SQL produced by Django views, set `LOG_LEVEL=DEBUG` in `.env`
and read `logs-web` — Django's query logger surfaces there with
the request's `request_id` attached.

## logs-redis — Channels backend / Celery broker

**When:** WS broadcasts don't reach other connections in the same
room, Celery tasks aren't being picked up.

```bash
make logs-redis | grep -iE "error|warning"
```

Redis is mostly silent in healthy runs. If `logs-redis` is empty
during a problem, the issue is upstream (the producer never
published) — go back to `logs-web` / `logs-ws` / `logs-celery`.

## logs-mailhog — dev SMTP

**When:** password-reset / activation email "didn't arrive".

Mailhog catches every outbound email locally — nothing leaves the
machine. Open the web UI at <http://localhost:8025> instead of
grepping logs; it shows full message bodies including HTML and
attachments. `make logs-mailhog` only confirms the SMTP handshake
happened.

## logs-ollama — local LLM

**When:** AI endpoint times out or returns gibberish.

```bash
make logs-ollama | grep "loading model"   # model swap on first call after idle
make logs-ollama | grep -iE "oom|memory"  # ran out of RAM
```

First request after the container starts (or after long idle)
triggers a model load — that's seconds of latency, not a hang.
If `loading model` appears every call, RAM pressure is evicting
the model between requests.

## Cross-service tracing

For an AI request that touches `web → celery → ollama`, the same
`request_id` is bound across all three:

```bash
make logs           | grep ab12cd34ef56   # all services, one slice
```

This is the one case `make logs` (un-filtered) is preferable —
when you don't know yet which service the failure happened in.
