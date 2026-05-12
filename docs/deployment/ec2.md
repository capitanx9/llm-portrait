# AWS EC2 deployment

This page describes the AWS environment that the production deploy lives in: what already exists, where to find it, and which dials matter when something goes wrong. Day-to-day deploys happen via the CD pipeline (see [`development/ci-cd.md`](../development/ci-cd.md)); this page is for operators inheriting the box.

## What you end up with

- One EC2 instance in `eu-central-1` running Ubuntu 24.04, fronted by nginx + Let's Encrypt.
- A domain (`llm-portrait.gotdns.ch`) on a NoIP DDNS pointing at the EC2 Elastic IP.
- An ECR repository holding the application image.
- An IAM role for GitHub Actions (OIDC, no long-lived AWS keys).
- An IAM instance profile attached to the EC2, granting it read-only ECR.

## 1. AWS prerequisites

- An AWS account with billing set up.
- Region `eu-central-1` (Frankfurt). Cheap-ish, close to most EU users.
- An IAM admin user for clicking through the console (or AWS CLI, your choice).

The cost target is ~$30/month for `t3a.large` + EBS + Elastic IP. Stop the instance whenever the project isn't being demoed to drop EBS-only cost.

## 2. EC2 instance

- **Type:** `t3a.large` (2 vCPU, 8 GB RAM). Llama3.2:3b sits at ~3 GB resident; the rest of the stack (Postgres, Redis, web, ws, celery, mailhog, nginx, certbot) fits comfortably. A `t3a.medium` (4 GB) would OOM under the model.
- **AMI:** Ubuntu Server 24.04 LTS, `x86_64`. Don't pick `arm64` — Mailhog publishes only `linux/amd64` images and will run under emulation otherwise.
- **Storage:** 30 GB `gp3` root volume. The Llama model alone is ~2 GB, plus the Postgres data, plus Docker images. 8 GB default is too small.
- **Key pair:** ED25519. The private key is stored in a password manager; the public key is registered on the instance. Anyone inheriting the box also inherits the key from the same manager.
- **Elastic IP:** allocate one, attach to the instance. The public IPv4 of an EC2 changes on stop/start otherwise — and the DDNS A record points at this IP.

## 3. Security group

Inbound rules (IPv4 + IPv6):

| Port | Protocol | Source     | Purpose                |
|------|----------|------------|------------------------|
| 22   | TCP      | your IP    | SSH (lock down to your home IP if you want) |
| 80   | TCP      | `0.0.0.0/0`, `::/0` | HTTP, redirect to HTTPS, ACME challenge |
| 443  | TCP      | `0.0.0.0/0`, `::/0` | HTTPS  |

No outbound rules to lock down — instance pulls images from ECR and the Llama model from `ollama.ai`, both over HTTPS.

## 4. ECR repository

A private repository named `llm-portrait` in the `eu-central-1` region holds the application image. The CD pipeline pushes two tags on every successful build: `:latest` (what the EC2 box pulls) and `:<git-sha>` (immutable, lets you roll back to a specific commit via `docker pull <registry>/llm-portrait:<sha>`).

Settings worth knowing if you need to touch it:

- **Visibility** — private. The EC2 instance authenticates via its IAM role (§5), GitHub Actions via OIDC (§5).
- **Tag mutability** — mutable. `:latest` gets overwritten by every deploy.
- **Lifecycle policy** — none. Old `:<git-sha>` tags accumulate; clean them up by hand if storage cost matters.

## 5. IAM roles

Two roles do the auth work, both already provisioned. No long-lived AWS access keys exist anywhere — neither role uses them.

### `llm-portrait-github-actions` (CD pipeline → AWS)

Used by GitHub Actions to push images to ECR. Trust policy federates on the [GitHub OIDC provider](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html) and restricts assumption to workflows from this specific repo via a `StringLike` on `token.actions.githubusercontent.com:sub` (`repo:capitanx9/llm-portrait:*`).

- Permissions: `AmazonEC2ContainerRegistryPowerUser` (scoped to the `llm-portrait` repo).
- Role ARN goes into the `AWS_ROLE_TO_ASSUME` GitHub secret — see [`development/ci-cd.md`](../development/ci-cd.md).

To inspect: AWS Console → IAM → Roles → `llm-portrait-github-actions`. The trust policy and attached policies tabs are the two places anything ever needs changing.

### `llm-portrait-ec2` (instance profile → ECR)

Attached to the EC2 instance as its instance profile. Lets the box do `aws ecr get-login-password ...` during a deploy without storing credentials.

- Trust policy: `ec2.amazonaws.com`.
- Permissions: `AmazonEC2ContainerRegistryReadOnly`.

To inspect: AWS Console → EC2 → instance → Security → IAM role.

## 6. Domain (NoIP)

[NoIP](https://www.noip.com) gives one free DDNS hostname. We use `llm-portrait.gotdns.ch`.

1. Create a free NoIP account.
2. Create a hostname `llm-portrait.gotdns.ch`, type A, target = the Elastic IP from step 2.
3. **NoIP free plan reminds you to confirm the hostname every 30 days.** Set a calendar reminder.

DuckDNS was tried first but its DNS occasionally returns SERVFAIL during Let's Encrypt's ACME-DNS check, which broke renewals. NoIP has been stable.

## 7. Server bootstrap

SSH into the box (`ssh -i ~/.ssh/strongbox ubuntu@<elastic-ip>`).

### Install Docker

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin curl
sudo usermod -aG docker ubuntu
# log out and back in for the group change to take effect
```

### Install AWS CLI v2

Needed for `aws ecr get-login-password` during deploys.

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
unzip awscliv2.zip
sudo ./aws/install
rm -rf awscliv2.zip aws/
```

### Create the project directory

```bash
sudo mkdir -p /opt/llm-portrait/docker
sudo chown -R ubuntu:ubuntu /opt/llm-portrait
cd /opt/llm-portrait
```

### Copy infra files (bootstrap only)

The CD pipeline now `scp`s `docker-compose.prod.yml` and `docker/nginx.conf` to `/opt/llm-portrait/` on every deploy, but for the very first deploy these files need to be on the box already. From your laptop in the project root:

```bash
scp docker-compose.prod.yml ec2-llm-portrait:/opt/llm-portrait/
scp docker/nginx.conf       ec2-llm-portrait:/opt/llm-portrait/docker/
```

(`ec2-llm-portrait` is the host alias in your local `~/.ssh/config`.) After the first successful CD run, the pipeline keeps these files in sync; you only ever edit them in the repo.

### Create `.env` on the box

```bash
nano /opt/llm-portrait/.env
```

Paste the prod values. Required keys:

```
SECRET_KEY=<long random string>
DEBUG=False
ALLOWED_HOSTS=63.183.30.218,llm-portrait.gotdns.ch
DJANGO_SETTINGS_MODULE=app.config.settings.prod

DATABASE_URL=postgres://app:<strong-password>@db:5432/llm_portrait
DB_NAME=llm_portrait
DB_USER=app
DB_PASSWORD=<strong-password>

CELERY_BROKER_URL=redis://redis:6379/0
REDIS_CACHE_URL=redis://redis:6379/1
REDIS_CHANNELS_URL=redis://redis:6379/2

OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2:3b
LLM_RATE_LIMIT=2/m
AI_TASK_TEMPERATURE=0.2

EMAIL_HOST=mailhog
EMAIL_PORT=1025
EMAIL_USE_TLS=False
DEFAULT_FROM_EMAIL=noreply@llm-portrait.gotdns.ch

# JSON logs in prod so log shippers (CloudWatch / Loki) parse them
# without a custom regex. Switch to "human" if you want to read raw
# `docker logs` on the box.
LOG_FORMAT=json
LOG_LEVEL=INFO

# Empty until the frontend is deployed at a separate origin. Comma-
# separated list once it is, e.g. https://app.llm-portrait.gotdns.ch
CORS_ALLOWED_ORIGINS=

ECR_REGISTRY=<account-id>.dkr.ecr.eu-central-1.amazonaws.com
ECR_REPOSITORY=llm-portrait
```

Back the file up to a password manager — secrets aren't in git for good reason. Never commit it.

## 8. First HTTPS certificate

Let's Encrypt's webroot challenge needs nginx running with an HTTP server block first. The repo's `nginx.conf` has both HTTP (with the ACME location) and HTTPS server blocks. The HTTPS block, however, will refuse to start until the cert files exist.

Two ways to handle this. The pragmatic one:

1. Make a temporary backup of `nginx.conf`:

   ```bash
   cp /opt/llm-portrait/docker/nginx.conf /opt/llm-portrait/docker/nginx.full.conf
   ```

2. Strip out the entire `server { listen 443 ssl; ... }` block from `nginx.conf` so only the HTTP server remains.
3. Bring nginx + certbot up:

   ```bash
   docker compose -f docker-compose.prod.yml up -d nginx certbot
   ```

4. Request the cert:

   ```bash
   docker compose -f docker-compose.prod.yml run --rm certbot \
     certonly --webroot -w /var/www/certbot \
     -d llm-portrait.gotdns.ch \
     --email <your-email> --agree-tos --no-eff-email
   ```

5. Once the cert appears in the `certbot_certs` named volume, restore the full nginx config:

   ```bash
   mv /opt/llm-portrait/docker/nginx.full.conf /opt/llm-portrait/docker/nginx.conf
   docker compose -f docker-compose.prod.yml restart nginx
   ```

The cert auto-renews via the certbot service's loop (every 12h, no-op until the cert is in the renewal window).

## 9. First start of the application stack

```bash
cd /opt/llm-portrait

# Login to ECR so docker compose pull can fetch the latest image.
aws ecr get-login-password --region eu-central-1 \
  | docker login --username AWS --password-stdin <account-id>.dkr.ecr.eu-central-1.amazonaws.com

# Pull and start everything.
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

Then prepare the application:

```bash
# Migrations are idempotent and the entrypoint runs them, but it's good to verify.
docker compose -f docker-compose.prod.yml exec web python manage.py migrate

# Create a superuser for /admin/.
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

# Pull the LLM model — one time, ~5–10 min over EC2's network.
docker compose -f docker-compose.prod.yml exec ollama ollama pull llama3.2:3b
```

Smoke-test the public domain with three independent paths — REST through gunicorn, REST through DRF, and the WebSocket service's HTTP side through daphne. Together they prove every public surface is alive after the deploy.

```bash
# REST via gunicorn (legacy Lab 2 endpoint, still served)
curl -fsS https://llm-portrait.gotdns.ch/health/
# {"status":"ok"}

# REST via DRF (the API surface)
curl -fsS https://llm-portrait.gotdns.ch/api/health/
# {"status":"ok"}

# WebSocket service, HTTP path (the AsyncAPI viewer is served by daphne)
curl -fsS -o /dev/null -w "%{http_code}\n" https://llm-portrait.gotdns.ch/ws/docs/
# 200
```

The same three checks plus a fourth — an anonymous WebSocket upgrade to `/ws/chat/smoke/` expecting HTTP 403 — run as a CD smoke-test on every deploy. The fourth check covers the WebSocket upgrade path itself (different code in nginx and daphne than the HTTP-only viewer), so REST, DRF, ws-HTTP, and ws-upgrade are all green or the deploy is marked red. See [`development/ci-cd.md`](../development/ci-cd.md).

For a richer manual smoke-test, point the Bruno collection at the `prod` environment, log in as a demo user (created via `make seed-users` inside the `web` container), and exercise REST + WS + AI. Cold Ollama loads the model on the first request after idle (30–60s); subsequent requests are 1–10s.

## 10. Auto-restart after reboot

Two layers cover this:

- **Docker daemon must start at boot.** It does on Ubuntu by default; verify with `sudo systemctl is-enabled docker` (should print `enabled`).
- **Compose services must come back up.** `docker-compose.prod.yml` sets `restart: unless-stopped` on every long-running service. Combined with the daemon being enabled, all containers start automatically after `sudo reboot`.

Verify by rebooting the instance, waiting ~2 min, then `docker compose -f docker-compose.prod.yml ps` — everything should be `Up` again.

If you ever want explicit control (`systemctl start/stop llm-portrait`), drop in a tiny systemd unit:

```ini
# /etc/systemd/system/llm-portrait.service
[Unit]
Description=llm-portrait docker compose stack
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/llm-portrait
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
TimeoutStartSec=600

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable llm-portrait.service
```

This is optional — `restart: unless-stopped` already covers reboots.

## 11. Deploys

Day-to-day deploys are fully automated by the [CD pipeline](../development/ci-cd.md). On every push to `main` that passes CI:

1. The pipeline builds the image, pushes `:latest` and `:<git-sha>` to ECR.
2. It `scp`s the current `docker-compose.prod.yml` and `docker/nginx.conf` from the repo to `/opt/llm-portrait/` on the box (the repo is the source of truth).
3. It SSHs in, runs `docker compose -f docker-compose.prod.yml pull && up -d --force-recreate`, and prunes the previous image.
4. It runs the four-path smoke-test against the public domain (`/health/`, `/api/health/`, `/ws/docs/`, plus an anonymous WS handshake).

Manual intervention is only needed for things outside the repo:

- **`.env` changes** — `.env` lives on the box (it has secrets that aren't in git). Edit it in place, then `docker compose -f docker-compose.prod.yml up -d --force-recreate web ws celery` so all containers boot from the new env.
- **Bootstrap-time work** — first cert (§8), first model pull (§9), first superuser. Once.
- **Disaster recovery** — see §10 / `restart: unless-stopped`. After a reboot everything comes back on its own.

`--force-recreate` matters here: editing a bind-mounted file (or env-file) doesn't trigger a recreate on its own; the container would keep its original config until something else changes.
