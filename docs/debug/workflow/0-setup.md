# Scenario 0 — Bring up the stack with demo data

**Goal:** a fresh clone runs, has data you can poke at, and a Bruno
collection wired up to it.

## Stack and data

```bash
git clone … && cd llm-portrait
cp .env.example .env
make up
make migrate
make seed-all
```

`make seed-all` creates 5 demo users, 3 demo rooms, and 18 messages
per room. All demo passwords are `pass1234`. Idempotent — safe to
re-run.

## Bruno collection (one-time)

In Bruno: **Open Collection** → point it at
[`bruno/llm-portrait/`](../../../bruno/llm-portrait/). Activate the
`local` environment (top-right dropdown). Run `auth/login.bru` once
— the post-response script writes `{{access_token}}` into the
environment, and every other request picks it up automatically.

The default credentials in the collection are `oleksa` / `pass1234`,
matching `make seed-users`. No manual edits needed.

A 200 from `auth/login.bru` means the stack is healthy: web is up,
db migrated, seed data present, JWT issuance works.

From here, any scenario in this folder assumes the collection is
loaded and `{{access_token}}` is populated.

## Reset

```bash
make flush-demo    # remove only seeded users / rooms / messages
make reset-db      # wipe Postgres only (keeps Ollama model + Redis)
make reset-ollama  # wipe the Llama model (~2 GB re-pull on next AI call)
make reset-redis   # restart Redis (flushes cache + Channels groups + Celery queue)
make reset-all     # nuclear: drop all volumes, rebuild, re-pull model
```

`flush-demo` leaves real data alone (filters by demo usernames /
room names). Each `reset-*` target prompts with a 3-second cancel
window before destruction.
