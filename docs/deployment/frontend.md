# Frontend deployment

The production frontend lives in a separate repository
([`llm-portrait-frontend`](https://github.com/capitanx9/llm-portrait-frontend))
and is served from its own origin. This page documents the wiring
between the two — what the backend has to know about the frontend,
why the topology looks the way it does, and what to do on the EC2 box
to keep the two halves talking.

## Topology

Split origin. The browser sees two hostnames:

```
                      ┌────────────────────────────────────┐
                      │            browser                 │
                      └───────┬─────────────────┬──────────┘
                              │                 │
              static assets   │                 │ /api/*, /ws/*
                              ▼                 ▼
        ┌──────────────────────────┐   ┌────────────────────────┐
        │ CloudFront               │   │ nginx on EC2           │
        │ d16lbq7rem1z12           │   │ llm-portrait.gotdns.ch │
        │   .cloudfront.net        │   │                        │
        │                          │   │   /api/*  → web:8000   │
        │   S3 bucket via OAC      │   │   /ws/*   → ws:8001    │
        └──────────────────────────┘   └────────────────────────┘
```

- **Static SPA** — `https://d16lbq7rem1z12.cloudfront.net/*` →
  CloudFront → S3 bucket via OAC (no public S3 access).
- **REST** — `https://llm-portrait.gotdns.ch/api/*` → gunicorn.
- **WebSocket** — `wss://llm-portrait.gotdns.ch/ws/*` → daphne.

The frontend's RTK Query `baseUrl` is set explicitly to the backend
hostname (via build-time env var); the WebSocket URL is built the
same way.

## Why split origin (not CloudFront-as-single-origin)

A single-origin layout would put CloudFront in front of everything —
S3 for static, EC2 for `/api/*` and `/ws/*` — routing by path
pattern. That requires:

- A second origin (EC2) behind CloudFront, including WebSocket-aware
  cache behaviour.
- Path-pattern rules to send `/api/*` and `/ws/*` to EC2 while `/`
  stays on S3.
- A custom CloudFront cache policy that doesn't break long-lived WS
  connections.

Split origin needs **one CORS line** on the backend and **one
Origin-whitelist line** in the WebSocket validator. That's the whole
delta. It's also the pattern real products use (Stripe ships
`dashboard.stripe.com` + `api.stripe.com` + `js.stripe.com`), so the
shape isn't a downgrade — it's the industry default.

## <a id="dns"></a>Why a raw `*.cloudfront.net` URL (not a custom subdomain)

The frontend ships on CloudFront's own URL —
`d16lbq7rem1z12.cloudfront.net` — not on something like
`app.llm-portrait.gotdns.ch`. The reason is structural and lives in
the DNS layer the backend already uses.

- The backend domain `llm-portrait.gotdns.ch` lives in NoIP's
  **shared zone** (`gotdns.ch`). We rent a hostname inside a zone we
  don't own.
- NoIP's shared zone blocks records whose name starts with `_`
  (treats them as reserved). That means ACM's DNS-validation
  challenge — `_acme-challenge.<your-subdomain>.gotdns.ch` — cannot
  be added. ACM has nowhere to put the validation record, so it
  can't issue a cert for any custom CloudFront subdomain we'd point
  at the distribution.
- **Paid NoIP doesn't fix this.** Paid tiers lift host count limits
  and remove the 30-day confirmation cycle, but the shared-zone
  record-type restrictions are part of the zone, not the plan.

CloudFront's own `*.cloudfront.net` URL ships with a working
AWS-managed cert out of the box. No DNS work, no ACM, no NoIP
changes. So we use that.

**What it would take to get a custom frontend domain.** Buying a
proper second-level domain (Cloudflare Registrar / NoIP Registrar /
anywhere — ~$10–15/year). On a domain we own outright, ACM
validation works normally. That's an evening's work post-Lab and
explicitly out of scope here.

## Backend configuration

Two env vars on the EC2 box need to point at the frontend's
CloudFront origin. Both live in `/opt/llm-portrait/.env`:

| Variable | What reads it | Purpose |
|---|---|---|
| `CORS_ALLOWED_ORIGINS` | `django-cors-headers` | Allows REST preflight (`OPTIONS`) from the frontend origin; without this every cross-origin REST call returns CORS errors in the browser. |
| `WS_ALLOWED_ORIGINS` | Channels' `OriginValidator` | Allows the WebSocket handshake from the frontend origin; without this `wss://.../ws/chat/...` returns 403 on upgrade. |

Both take a comma-separated list of origin URLs (scheme + host +
port, no path). For the live deploy:

```
CORS_ALLOWED_ORIGINS=https://d16lbq7rem1z12.cloudfront.net
WS_ALLOWED_ORIGINS=https://d16lbq7rem1z12.cloudfront.net
```

Apply on the box:

```bash
ssh ec2-llm-portrait
sudo nano /opt/llm-portrait/.env
# set the two variables above
cd /opt/llm-portrait
docker compose -f docker-compose.prod.yml up -d --force-recreate web ws celery
```

`--force-recreate` is mandatory — editing the env file alone doesn't
trigger a restart, so without it the containers keep the old values
in memory.

## Frontend-side setup (out of scope, link only)

The S3 bucket, CloudFront distribution, OAC, ACM cert, and the
GitHub Actions OIDC role for the frontend's CD pipeline live in the
frontend repo. Single source of truth:
[`llm-portrait-frontend/docs/deployment/s3-cloudfront.md`](https://github.com/capitanx9/llm-portrait-frontend/blob/main/docs/deployment/s3-cloudfront.md).
This page does not duplicate it.

## Smoke test after wiring

Once both env vars are set on EC2 and the containers have been
recreated:

1. Open `https://d16lbq7rem1z12.cloudfront.net/` in a browser — the
   SPA loads.
2. Register a new user via the UI. REST call to
   `https://llm-portrait.gotdns.ch/api/auth/register/` returns 201;
   DevTools → Network shows the CORS preflight `OPTIONS` returned
   200 with `Access-Control-Allow-Origin` set to the CloudFront URL.
3. Log in, open a room — the WebSocket upgrade to
   `wss://llm-portrait.gotdns.ch/ws/chat/<room>/?token=…` returns
   `101 Switching Protocols`. If the env edit didn't apply, this
   step returns `403` because `OriginValidator` rejects the
   handshake before auth runs.
4. Send a chat message from a second incognito window logged in as
   another user — both windows see the message in real time.
5. Optional: trigger a translate. `POST /api/ai/process/` returns
   200 with `source_language` and `translation` in the body.

If any step 401/403s, the operational env edit on EC2 did not take
effect. The CD smoke test on the backend side does **not** exercise
CORS preflight or cross-origin WS — those are covered only by the
manual flow above.
