# Step-debugger (VS Code attach mode)

How to pause the running Django process inside Docker and walk through
the code line by line from VS Code.

For the other debug surfaces, see:

- [`logging.md`](logging.md) — loguru, request_id, access log, body dump
- [`http.md`](http.md) — Swagger UI as a debugging tool
- [`ws.md`](ws.md) — `make ws-demo`, Postman, reading `make logs-ws`

## How attach mode works

Our backend runs as a long-lived **server** (Django) inside a container.
There is no "run with debugger" button that starts and debugs in one
click, because the server is already running by the time you want to
look at it. So the flow is split in two:

1. The **server side** opens a debug port. Inside the container,
   `debugpy.listen(:5678)` says "any IDE that connects here can drive
   me." The server then keeps serving requests as normal — debugpy is
   passive until somebody connects.

2. The **client side** is VS Code. It opens a TCP connection to that
   port. From that moment on, VS Code knows about your breakpoints and
   can pause the server's Python interpreter when one is hit.

Both sides have to be alive at the same time. The server side is what
`make up-debug` gives you. The client side is what the green ▶ button
in VS Code's *Run and Debug* panel gives you.

When you trigger a request afterwards (Swagger UI, browser, curl), it
flows through Django; if it hits a line with a breakpoint, debugpy
tells VS Code to pause and you see the frozen state in the editor.

## Workflow

### 1. Start the stack with debugpy enabled

```bash
make up-debug
```

This is `make up` with `DEBUGPY=1` set. The web container imports
`debugpy`, opens port `5678`, and disables Django's autoreload (it
plays badly with debugpy's path tracking). Without the flag none of
this happens and there is no overhead.

Verify it's listening:

```bash
make logs-web
```

You should see:

```
debugpy listening on :5678 (attach when you want)
Starting ASGI/Daphne development server at http://0.0.0.0:8000/
```

### 2. Set a breakpoint

Open the file you want to inspect (any file under `src/` or `tests/`).
Click on the **line number** of the line where execution should pause
— a red dot appears.

You can have many breakpoints. Click again to remove one.

### 3. Attach VS Code

`Cmd+Shift+D` (or the bug icon in the left sidebar) → the dropdown at
the top says *"Attach to web (Django) container"* → click the green ▶.

The status bar at the bottom of VS Code turns **orange** and a
floating debug toolbar appears. That's the signal you're attached.

### 4. Trigger the code

Whatever entry point exercises the line you care about:

- **REST endpoint** — open Swagger at <http://localhost:8000/api/docs/>,
  pick the operation, click *Try it out*, *Execute*. It hangs while
  Django is paused on your breakpoint.
- **Background work** — call the management command, fire the Celery
  task, etc. Same effect.

VS Code jumps to the file, highlights the paused line and shows the
current state.

### 5. Switch back to normal mode

```bash
make down
make up
```

Restores autoreload and turns the debugger off — that's how you want
the stack the rest of the time.

## "Wait until I attach" mode

If the code you want to break on runs only **once during boot**
(signals, app config, the first imports), the server's already past
that point by the time you click ▶ in VS Code. For these cases:

```bash
make up-debug-wait
```

The web process opens `:5678` and **blocks** until you attach. As soon
as VS Code connects, it continues. Useful for one-shot startup code.

## Path mappings

`.vscode/launch.json` maps the workspace root on your Mac to `/app`
inside the container so the breakpoints you set bind to the right
lines on the running process. There's nothing to configure unless you
change the working directory layout.

## When not to use the debugger

For most bugs a `logger.info(...)` plus a tailed service log is faster
than attaching — see [`logging.md`](logging.md). Reach for the debugger
when the bug is in branching logic, async flow, or when you genuinely
need to walk a complex object live.
