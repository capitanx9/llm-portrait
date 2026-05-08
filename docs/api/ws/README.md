# WebSocket API

Real-time chat over WebSocket. Documented as an
[AsyncAPI 3.1](https://www.asyncapi.com/) specification — the
event-driven equivalent of OpenAPI.

## Live documentation

When the stack is up, the rendered spec is reachable at:

- **AsyncAPI viewer:** <http://localhost:8000/ws/docs/> — channels,
  message schemas, security scheme, examples. Pre-rendered from the
  YAML below; not interactive (you can't "Try it out" the way you can
  in Swagger UI for REST). See [GUI client](#gui-client) below for
  hands-on exploration.

In production the same page lives at
<https://llm-portrait.gotdns.ch/ws/docs/>.

## Source files

- [`asyncapi.yaml`](asyncapi.yaml) — the spec. Edit this when the wire
  protocol changes (new message type, new field, security tweak).
- [`asyncapi.html`](asyncapi.html) — pre-rendered viewer, generated
  from the YAML. Treat it like `poetry.lock`: regenerated locally,
  committed alongside the YAML edit.
- [`../../../bruno/`](../../../bruno/) — Bruno collection with the
  WebSocket request and four pre-saved messages, alongside the REST
  endpoints. Open the collection's `ws/chat-room.bru` to drive the
  socket from a GUI.

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

## GUI client

The full Bruno collection at [`bruno/`](../../../bruno/) covers the
WS handshake plus four pre-saved messages on `ws/chat-room.bru`:
valid frame, empty text, long text, and an invalid-JSON case (paste
raw, switch the message type to *Text*). The Login script writes the
JWT into `{{access_token}}`, which the WS URL picks up via
`?token={{access_token}}`.

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
