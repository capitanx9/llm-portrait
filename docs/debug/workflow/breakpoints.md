# Setting breakpoints in VS Code

For debugpy wiring details see
[`../architecture/debugpy.md`](../architecture/debugpy.md).

## 1. Start with debugpy

```bash
make up-debug
```

Use `make up-debug-wait` if you need to break on startup-only code
(signals, `AppConfig.ready`, first imports) — the web process blocks
until VS Code attaches.

Verify it's listening:

```bash
make logs-web
# expect: "debugpy listening on :5678 (attach when you want)"
```

## 2. Set a breakpoint

Open any file under `src/` or `tests/` and click the line number
where execution should pause — a red dot appears.

## 3. Attach VS Code

Run and Debug panel → "Attach to web (Django) container" → click ▶.
The bottom bar turns orange; you're attached.

## 4. Trigger the code

Issue the request via:

- **Swagger UI** at `http://localhost:8000/api/docs/` — *Try it out*
- **Bruno** at `bruno/llm-portrait/`
- `curl`

Django pauses on the breakpoint; VS Code highlights the line and
shows local state.

## 5. Switch back to normal mode

```bash
make down
make up
```

Restores autoreload and stops debugpy.

## When to use the debugger

Branching logic, async flow, or walking a complex object live.

For most bugs a `logger.info(...)` plus
[tailed logs](logs.md) is faster.
