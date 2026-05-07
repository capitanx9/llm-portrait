# Postman collection

Hands-on Postman artefacts for the WebSocket chat API.

## Recommended: open the live collection

The collection lives in a public Postman workspace, fork it into your
own account in one click:

> <https://www.postman.com/workspace/LLM-Portrait~5ea18d06-4274-46ad-94f5-37aae5a07b60/collection/69fcd027fa9ca218b33a5171?action=share&source=copy-link&creator=6728552>

This is the working-as-intended path: `Chat room (WS)` is a real
WebSocket request in Postman, the saved messages are bound to it, and
nothing has to be reconstructed by hand. Pair it with one of the two
exported environments below by importing them through the Postman GUI.

## Files in this folder

| File | What it is |
|---|---|
| `llm-portrait-ws.postman_collection.json` | Collection v2.1 export (Login + Register + Chat room) |
| `llm-portrait-local.postman_environment.json` | Environment pointing at `localhost:8000` / `localhost:8001` |
| `llm-portrait-prod.postman_environment.json` | Environment pointing at `llm-portrait.gotdns.ch` |

## Known issue: WebSocket request demotes to HTTP GET on import

When you import `llm-portrait-ws.postman_collection.json` through
Postman's *Import* dialog, the `Chat room (WS)` request comes in as a
plain HTTP GET instead of a WebSocket request. This is a documented
limitation of Postman's collection v2.1 schema — it doesn't yet have
first-class fields for `protocol: ws` items, so the export round-trip
loses the WebSocket nature of the request. The same JSON file that was
*exported* by Postman doesn't *re-import* correctly.

We're keeping the file in the repo on purpose:

- It's still useful for the two HTTP requests (Login, Register).
- When Postman ships proper WS support in their collection schema, the
  same file will start importing correctly without changes on our end.
- It documents what the WS request *should* be, even if Postman can't
  reconstruct it from JSON.

### Workarounds

- **Use the live workspace link above.** That's the simplest path —
  `Chat room (WS)` is a real WS request there, no JSON round-trip.
- **Or:** import the JSON, then in Postman manually delete the imported
  `Chat room (WS)` HTTP request, create a new **WebSocket** request
  with the URL `{{base_ws}}/ws/chat/{{room}}/?token={{access_token}}`
  and add it to the collection. The four sample messages from the
  AsyncAPI spec at `/ws/docs/` are listed in
  [`../README.md`](../README.md) — paste them as Saved Messages by
  hand.
- **Or:** drop Postman entirely and use `make ws-demo` from a terminal,
  which automates the same two-user chat scenario with `websocat`. See
  [`../../../debug/ws.md`](../../../debug/ws.md).
