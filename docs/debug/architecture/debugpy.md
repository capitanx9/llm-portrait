# debugpy architecture

[debugpy](https://github.com/microsoft/debugpy) listens for VS Code
attach in the dev container only. Production image doesn't ship it.

## Wiring

- Hook: `manage.py` opens `:5678` when `DEBUGPY=1` is set in the
  container environment
- Gating: `DEBUGPY=1` enables; `DEBUGPY_WAIT=1` makes the process
  block until VS Code connects (useful for breakpoints in startup
  code, signals, app config)
- Autoreload: disabled when `DEBUGPY=1` — debugpy and Django's
  `StatReloader` fight over file paths; the dev compose adds
  `--noreload` automatically
- Image: dev-only. Production Dockerfile stage doesn't install
  debugpy
- Port: `5678`, exposed by `docker-compose.dev.yml`

## Configuration

| Env var | Effect |
|---|---|
| `DEBUGPY=1` | Open `:5678`, disable autoreload |
| `DEBUGPY_WAIT=1` | Also block boot until VS Code attaches |

## VS Code side

`.vscode/launch.json` defines an attach configuration with
`pathMappings: ${workspaceFolder} ↔ /app` so breakpoints set in the
host editor bind to lines in the running container.

`.vscode/extensions.json` recommends Python + ruff + REST Client
extensions to anyone opening the project.
