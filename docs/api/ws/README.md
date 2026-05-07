# WebSocket API

Real-time chat over WebSocket. Documented as an
[AsyncAPI 3.1](https://www.asyncapi.com/) specification — the
event-driven equivalent of OpenAPI.

## Live documentation

When the stack is up, the rendered spec is reachable at:

- **AsyncAPI viewer:** <http://localhost:8000/ws/docs/> — channels,
  message schemas, security scheme, examples. Pre-rendered from the
  YAML below; not interactive (you can't "Try it out" the way you can
  in Swagger UI for REST). See [Postman](#postman-collection) below
  for hands-on exploration.

In production the same page lives at
<https://llm-portrait.gotdns.ch/ws/docs/>.

## Source files

- [`asyncapi.yaml`](asyncapi.yaml) — the spec. Edit this when the wire
  protocol changes (new message type, new field, security tweak).
- [`asyncapi.html`](asyncapi.html) — pre-rendered viewer, generated
  from the YAML. Treat it like `poetry.lock`: regenerated locally,
  committed alongside the YAML edit.
- [`postman/`](postman/) — hand-maintained Postman collection for
  hands-on poking at the WS API.

## Local toolchain

```bash
make asyncapi-validate    # validate docs/api/ws/asyncapi.yaml
make asyncapi-build       # regenerate docs/api/ws/asyncapi.html
```

Both commands run against the official `asyncapi/cli` Docker image, so
no Node/npm needs to be installed on the host. CI runs the validate
step on every PR, so a malformed YAML can't merge.

## Why pre-rendered, not server-rendered

The AsyncAPI HTML template needs Node + npm + a few MB of bundler deps
that have no business inside a Python runtime image. Rebuilding on
every commit through CI was tempting but creates a class of bug where
the YAML and the HTML drift out of sync silently — committing the
generated HTML keeps the diff visible in PRs.

## Postman collection

For poking the WS API from a GUI we ship a hand-maintained Postman
collection plus two environments. The recommended path is to **fork
the live collection** from the public Postman workspace:

> <https://www.postman.com/workspace/LLM-Portrait~5ea18d06-4274-46ad-94f5-37aae5a07b60/collection/69fcd027fa9ca218b33a5171?action=share&source=copy-link&creator=6728552>

Pair it with one of the two environments shipped under
[`postman/`](postman/):

- `llm-portrait-local.postman_environment.json` — local stack.
- `llm-portrait-prod.postman_environment.json` — deployed instance.

### Why a live link, not just JSON files

Postman's collection v2.1 export format doesn't have first-class
fields for WebSocket requests — the `Chat room (WS)` item demotes to
an HTTP GET on JSON round-trip. Importing
`postman/llm-portrait-ws.postman_collection.json` works for the two
HTTP requests (Login, Register) but the WS request needs to be
recreated by hand. The live link side-steps that.

The JSON file is still committed: it's useful for the HTTP requests,
and once Postman ships proper WS support in their schema, the same
file will start importing correctly without changes from us. See
[`postman/README.md`](postman/README.md) for the full workaround.

### Run order

1. **Login (get JWT)** — POSTs to `/api/auth/login/` with the demo
   credentials; a post-response script writes the access token into
   the collection variable `access_token`.
2. **Register (one-time)** — only needed on a fresh server. 400 on
   re-run means the demo user already exists, that's fine.
3. **Chat room (WS)** — opens the WebSocket connection and lets you
   send each of the four documented messages (valid, empty, long,
   invalid JSON) by typing them into the message editor and clicking
   **Send**. The token from step 1 is plugged into the `?token=`
   query parameter automatically.

### Sample messages

Paste any of these into Postman's message editor for the Chat room
request:

```json
{"text": "hello from postman"}
```

```json
{"text": ""}
```

```json
{"text": "много много много много много много много букв"}
```

For the invalid-JSON path, switch the message type from JSON to Text
and send any non-JSON string, e.g. `просто строка не json`. The
server responds with `{"error": "invalid_json", ...}` and keeps the
connection open.

For internal debugging tips and `make logs-ws` traces, see
[`../../debug/ws.md`](../../debug/ws.md).

## Wire protocol summary

The full schema lives in [`asyncapi.yaml`](asyncapi.yaml); the short
version:

| Direction | Message | Shape |
|---|---|---|
| client → server | `ChatMessageIn` | `{"text": "..."}` |
| server → client | `ChatMessageOut` | `{"id", "sender", "text", "created_at"}` |
| server → client | `InvalidJsonError` | `{"error": "invalid_json", "detail": "..."}` |
| server → client | `InternalError` | `{"error": "internal", "detail": "..."}` |

Authentication is JWT, passed as `?token=<access>` on the upgrade URL.
Browsers can't set custom headers on `WebSocket(...)` constructors,
which is why the query string is the documented place.

For internal debugging tips and `make logs-ws` traces, see
[`../../debug/ws.md`](../../debug/ws.md).
