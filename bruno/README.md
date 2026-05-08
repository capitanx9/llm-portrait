# Bruno collection

Hands-on API collection for the LLM-Portrait project. Built with
[Bruno](https://www.usebruno.com/) — a git-native, open-source
alternative to Postman that stores requests as plain `.bru` text
files. WebSocket requests are first-class (unlike Postman, where the
v2.1 export schema couldn't represent them).

## Layout

```
bruno/llm-portrait/
├── bruno.json              ← collection manifest
├── collection.bru          ← shared variables (username, password, room)
├── environments/
│   ├── local.bru           ← localhost:8000 (HTTP) + localhost:8001 (WS)
│   └── prod.bru            ← https://llm-portrait.gotdns.ch
├── auth/                   ← Register, Login, Refresh, Me, Logout
├── chat/                   ← List rooms, Create room, Get messages
├── ai/                     ← Translate ru→en, Translate en→fr, Summarize
├── ws/                     ← Chat room (real WebSocket request, 4 saved messages)
└── edge-cases/
    ├── auth/               ← 401 wrong password, 401 no token
    ├── chat/               ← 401 no token
    └── ai/                 ← 400 missing field, 400 unknown action, 401 no token
```

One collection covers REST and WebSocket together. That's the whole
point of Bruno — `meta { type: ws }` requests live in the same tree
as `meta { type: http }` requests.

## How to open

1. Install Bruno (>=2.13.0 for WebSocket support):
   - macOS: `brew install --cask bruno`
   - or download from <https://www.usebruno.com/downloads>
2. Open Bruno → **Open Collection** → pick `bruno/llm-portrait/`.
3. Pick the environment from the dropdown in the top-right
   (`local` or `prod`).
4. Run requests top-to-bottom following the scenarios below.

The Login script writes both `access_token` and `refresh_token` into
collection variables, so anything downstream that needs `Bearer
{{access_token}}` works without copy-pasting tokens.

## Scenarios

A "scenario" is what you do, not what's in the collection. Pick one,
run the listed requests in order. Bruno's *Run Collection* dialog
lets you select a subset and run them automatically; a manual click
top-to-bottom works just as well.

| Scenario | Requests, in order | When to use |
|---|---|---|
| **Onboarding** | auth/register → auth/login → auth/me | First time on a fresh DB. |
| **Daily auth check** | auth/login → auth/me | "Is the backend alive?" |
| **Chat smoke (REST)** | auth/login → chat/create-room → chat/list-rooms → chat/get-room-messages | When touching chat REST views. |
| **AI smoke** | auth/login → ai/translate-ru-en → ai/summarize | When touching LangGraph. |
| **Token rotation** | auth/login → auth/refresh → auth/me → auth/logout | When touching JWT. |
| **Realtime chat (WS)** | auth/login → ws/chat-room (open the connection, send saved messages) | When touching the WS consumer. |
| **Full E2E** | register → login → create-room → ai/summarize → logout | Demo or release smoke. |

## WebSocket

`ws/chat-room.bru` is a **real** WebSocket request — Bruno opens a
persistent connection, you can pick from four pre-saved messages and
send them through the same socket:

- `hello` — typical valid frame
- `empty text` — exercises the empty-string branch
- `long text` — exercises the long-string branch
- `invalid json (paste raw, switch to text)` — switch the message
  type to *Text* in Bruno, send `просто строка не json` to exercise
  the `invalid_json` error path. The server responds with
  `{"error": "invalid_json", ...}` and keeps the connection open.

The token from `auth/login` is plugged into the WS URL via
`?token={{access_token}}` automatically.

## Why Bruno, not Postman

Migrated from Postman in May 2026. Reasons:

- **Plain text files**, one per request. PR diffs are readable; you
  can grep for endpoints; renames are file renames.
- **WebSocket support is first-class.** Postman's v2.1 export schema
  couldn't represent WS requests at all — they demoted to HTTP GET on
  every JSON round-trip. The v3 YAML format added WS support in the
  GUI but the CLI still mis-converts. Bruno just works.
- **Open source, free, no account required.** No "fork the live
  workspace" workarounds.
- **No vendor cloud sync.** The repo is the source of truth; nothing
  to keep in sync between cloud and disk.

## Why not bundle Bruno CLI tests in CI

Solo project, manual verification. Adding `bru run` to CI would be
duplicate effort with the existing pytest suite which already covers
each endpoint at a closer level (no JWT round-trip needed). Bruno
collection stays a developer / mentor / demo tool, not a test gate.

## Format reference

Bruno collection format ([`.bru` markup](https://docs.usebruno.com/bru-lang/overview)):

- `meta { name, type, seq }` — metadata. `type` is `http` or `ws`.
- `get/post/put/delete { url, body, auth }` — HTTP method block.
- `ws { url, auth }` — WebSocket connection block.
- `headers { ... }` — HTTP-level headers (also used for WS handshake).
- `body:json { ... }` — JSON request body.
- `body:ws { name, content }` — saved message for a WS request. Repeat
  the block for multiple presets.
- `auth:bearer { token }` — bearer-token auth.
- `script:post-response { ... }` — JS executed after a response. Use
  `bru.setVar("name", value)` to write variables.
- `tests { test("…", function() { … }) }` — assertions in JS.
