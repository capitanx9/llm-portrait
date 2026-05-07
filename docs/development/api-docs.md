# API documentation

The project speaks two transports — REST over HTTP and chat over
WebSocket — and we publish a separate spec for each, both reachable
from a running instance:

| Surface | Spec format | URL when the stack is up |
|---|---|---|
| REST | OpenAPI 3 (drf-spectacular) | [`/api/docs/`](http://localhost:8000/api/docs/) |
| WebSocket | AsyncAPI 3 | [`/ws/docs/`](http://localhost:8000/ws/docs/) |

The two pages cross-link to each other so an external reader landing
on either one can find the other.

## REST — generated at runtime

The OpenAPI schema is produced on the fly by `drf-spectacular` from
the actual DRF views, serializers and routers. There's nothing to
build — adding a new endpoint that's properly typed shows up in
Swagger UI on the next request to `/api/docs/`. Settings live under
`SPECTACULAR_SETTINGS` in `app.config.settings.base`.

## WebSocket — pre-rendered from a hand-written spec

Channels consumers aren't introspectable the way DRF views are
(there's no equivalent of `serializers` or routers that drf-spectacular
could read), and at the time of writing nobody publishes a usable
"spec generator" for Django Channels. So we maintain `docs/asyncapi.yaml`
by hand and ship a pre-rendered HTML page next to it.

### Source of truth

`docs/asyncapi.yaml` — AsyncAPI 3.0 document describing:
- the dev (`ws://localhost:8001`) and prod (`wss://...`) servers;
- the `/ws/chat/{name}/` channel with its `name` parameter;
- the four wire messages (`ChatMessageIn`, `ChatMessageOut`,
  `InvalidJsonError`, `InternalError`);
- the `sendMessage` / `receiveMessage` operations;
- the `?token=<jwt>` security scheme.

When the wire protocol changes, edit the YAML and regenerate the
HTML — the YAML is the spec, the HTML is the cached rendering.

### Validate locally

```bash
make asyncapi-validate
```

Runs the official `asyncapi/cli` Docker image against
`docs/asyncapi.yaml`. CI runs the exact same command (see the
`asyncapi` job in `.github/workflows/ci.yml`), so a YAML that fails
CI also fails on your laptop and vice versa.

### Regenerate the HTML

```bash
make asyncapi-build
```

Rewrites `docs/asyncapi.html` from the YAML using the official
`@asyncapi/html-template` (single-file output: HTML + inlined JS/CSS,
~500 KB). Commit the regenerated file alongside the YAML edit.

We don't run the build step in CI on purpose — committing
CI-generated artefacts is the kind of indirection that goes wrong
six months later when somebody forgets the workflow and edits the
HTML directly. Treat `asyncapi.html` like `poetry.lock`: regenerated
locally, reviewed in the diff, committed by hand.

### Why pre-rendered, not server-rendered

The HTML template needs Node + npm + a couple of MB of bundler deps,
and the project image is Python-only. Adding a Node toolchain to the
runtime image (or running a separate "docs" container) is not worth
the size and complexity for content that changes on the order of
"once per refactor."

The Django view at `app.core.views.asyncapi_docs` simply streams the
committed HTML file. If the file isn't there (e.g. a fresh checkout
that hasn't run `make asyncapi-build` yet) the view returns a `503`
with instructions instead of a confusing 500 — the surface is meant
to degrade visibly, not silently.
