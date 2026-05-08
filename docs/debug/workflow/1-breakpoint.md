# Scenario 1 — Stop inside a view

**Goal:** pause Python execution, inspect locals, step through.

## Start the stack in debug mode

```bash
make down
make up-debug
```

`up-debug` sets `DEBUGPY=1` (opens `:5678`) and `LOG_HTTP_BODY=1`
(body dump on the access log) in one shot. Autoreload is disabled
automatically — debugpy and Django's `StatReloader` don't coexist.

## `up-debug` vs `up-debug-wait`

debugpy opens a TCP port and listens. While no debugger is attached,
the Python process **runs as usual** — code executes, requests are
served, breakpoints simply don't fire (no one is listening for
events). The two Make targets differ in *when* the process is
allowed to start.

| | When does Django start? | When can VS Code attach? |
|---|---|---|
| `up-debug` | Immediately, regardless of debugger | Any time after boot |
| `up-debug-wait` | Only after VS Code attaches | Required at boot |

**Use `up-debug` for the common case.** You bring up the stack, then
attach VS Code whenever convenient, set a breakpoint in a view, and
hit the endpoint. The breakpoint fires because the debugger is
already attached by the time the request arrives.

**Use `up-debug-wait` only when the code you want to break in runs
at startup** — `AppConfig.ready()`, signal registration, lazy
settings, anything that executes once during Django boot. With plain
`up-debug` Django has already finished starting by the time you
attach, so the breakpoint never fires. `up-debug-wait` blocks the
process at the very first import, gives you time to attach, then
lets boot proceed under the debugger.

In practice 95% of debugging is regular views / consumers / Celery
tasks — i.e. `up-debug`. Reach for `up-debug-wait` only when you
*know* the target code runs during boot.

## Attach VS Code

`.vscode/launch.json` ships an attach configuration named
**Attach to web (5678)**. Open the Run panel → select it → start.

Path mappings (`${workspaceFolder}` ↔ `/app`) are pre-wired, so
breakpoints set in your host editor bind to the running container.

## Trigger from Bruno

Set a breakpoint in `src/app/chat/views.py` (or any view), then
send a request from Bruno that hits it. VS Code stops on the
breakpoint. Step over, watch, evaluate.

## Logs run in parallel

`make up-debug` doesn't replace the log workflow — it adds to it.
In a second terminal:

```bash
make logs-web
```

When you resume from the breakpoint, the access-log line for the
same request appears at the end. The `request_id` matches the
`X-Request-ID` returned to Bruno — that's the bridge to Scenario 2.

## Where it works and where it doesn't

debugpy is wired into `manage.py` and triggers for `runserver` and
`test`. It works for: views, consumers, middleware, Celery tasks,
signals — anything that runs inside the live `web` / `ws` /
`celery` process.

It does **not** trigger for one-shot `manage.py` commands run via
`docker exec` (seeds, migrations called by hand). For those, the
workaround is to drop a `breakpoint()` call in code or run the
command locally outside Docker with `python -m debugpy`. In
practice this is rarely needed — the project has no standalone
CLI code beyond the seeds.

## What you've used

- Surface 2 (debugpy): `make up-debug`, VS Code attach
- Surface 3 (trigger): Bruno HTTP request
- Surface 1 in parallel: `make logs-web` for the access line
