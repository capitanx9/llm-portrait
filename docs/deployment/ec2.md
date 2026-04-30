# AWS EC2 deployment

This page documents how the production environment was set up on AWS, in enough detail to reproduce it from scratch. Once it's set up, day-to-day work happens via the CD pipeline (see [`development/ci-cd.md`](../development/ci-cd.md)) — this page covers the one-time bootstrap.

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

- **Type:** `t3a.large` (2 vCPU, 8 GB RAM). Llama3.2:3b sits at ~3 GB resident; the rest of the stack (Postgres, Redis, web, celery, mailhog, nginx, certbot) fits comfortably. A `t3a.medium` (4 GB) would OOM under the model.
- **AMI:** Ubuntu Server 24.04 LTS, `x86_64`. Don't pick `arm64` — Mailhog publishes only `linux/amd64` images and will run under emulation otherwise.
- **Storage:** 30 GB `gp3` root volume. The Llama model alone is ~2 GB, plus the Postgres data, plus Docker images. 8 GB default is too small.
- **Key pair:** create a new ED25519 keypair, name it `strongbox`. Save the private key into a password manager (this project uses [Strongbox](https://strongboxsafe.com)). Upload the public key when launching the instance.
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

In the `eu-central-1` region:

```
Repositories → Create repository → "llm-portrait", private, mutable tags
```

The image will be pushed by the CD pipeline as both `:latest` and `:<git-sha>`.

## 5. IAM roles

### `llm-portrait-github-actions` (OIDC for the CD pipeline)

GitHub Actions authenticates to AWS via [OIDC federation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html). No long-lived `AWS_ACCESS_KEY_ID` is stored anywhere.

Steps:

1. **Create an OIDC identity provider** in IAM:
   - Provider URL: `https://token.actions.githubusercontent.com`.
   - Audience: `sts.amazonaws.com`.
2. **Create the role** `llm-portrait-github-actions`. Trust policy:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": { "Federated": "arn:aws:iam::<account-id>:oidc-provider/token.actions.githubusercontent.com" },
         "Action": "sts:AssumeRoleWithWebIdentity",
         "Condition": {
           "StringEquals": { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
           "StringLike":   { "token.actions.githubusercontent.com:sub": "repo:capitanx9/llm-portrait:*" }
         }
       }
     ]
   }
   ```

   The `StringLike` on `sub` is what restricts who can assume the role — only workflows from the `capitanx9/llm-portrait` repo.
3. **Attach permissions** — at minimum:
   - `AmazonEC2ContainerRegistryPowerUser` (or a custom policy with `ecr:GetAuthorizationToken`, `ecr:Batch*`, `ecr:PutImage`, `ecr:UploadLayerPart`, `ecr:InitiateLayerUpload`, `ecr:CompleteLayerUpload` on the `llm-portrait` repo).
4. **Note the role ARN** — goes into the `AWS_ROLE_TO_ASSUME` GitHub secret (see [`development/ci-cd.md`](../development/ci-cd.md)).

### `llm-portrait-ec2` (instance profile)

The EC2 instance pulls the latest image from ECR on every deploy. Using an instance profile avoids putting AWS keys on the box.

1. Create role `llm-portrait-ec2`, trust policy with `ec2.amazonaws.com` as the principal.
2. Attach `AmazonEC2ContainerRegistryReadOnly`.
3. Attach the role as the **instance profile** of the EC2 instance.

After this is in place, the AWS CLI on the box (or the CD pipeline running over SSH) can do `aws ecr get-login-password --region eu-central-1 | docker login ...` without any explicit credentials.

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

### Copy infra files from the repo

The CD pipeline only updates the Docker image. The compose file, the nginx config, and `.env` live on the box and are managed manually.

From your laptop (in the project root):

```bash
scp docker-compose.prod.yml ec2-llm-portrait:/opt/llm-portrait/
scp docker/nginx.conf       ec2-llm-portrait:/opt/llm-portrait/docker/
```

(`ec2-llm-portrait` is the host alias in your local `~/.ssh/config`.)

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

REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
REDIS_CACHE_URL=redis://redis:6379/1

OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2:3b
LLM_RATE_LIMIT=2/m

EMAIL_HOST=mailhog
EMAIL_PORT=1025
EMAIL_USE_TLS=False
DEFAULT_FROM_EMAIL=noreply@llm-portrait.gotdns.ch

GITHUB_OAUTH_CLIENT_ID=<from the prod OAuth App>
GITHUB_OAUTH_CLIENT_SECRET=<from the prod OAuth App>

ECR_REGISTRY=<account-id>.dkr.ecr.eu-central-1.amazonaws.com
ECR_REPOSITORY=llm-portrait
```

Back the file up to a password manager (this project keeps it in Strongbox under `llm-portrait-prod-env`). Never commit it.

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

Smoke-test:

```bash
curl -fsS https://llm-portrait.gotdns.ch/health/
# {"status":"ok"}
```

Now go to <https://llm-portrait.gotdns.ch/>, sign up, fill the profile, and click "Сгенерировать портрет". Generation takes 1–3 minutes on `t3a.large` (this is bare CPU inference; see [`overview.md`](../overview.md) for why).

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

## 11. Manual deploys (compose / nginx changes)

The CD pipeline updates the Docker image and runs `docker compose pull && up -d`. Anything outside the image — `docker-compose.prod.yml`, `docker/nginx.conf`, `.env` — needs to be pushed manually:

```bash
# from the project root on your laptop
scp docker-compose.prod.yml ec2-llm-portrait:/opt/llm-portrait/
scp docker/nginx.conf       ec2-llm-portrait:/opt/llm-portrait/docker/
```

Then on the box:

```bash
cd /opt/llm-portrait
docker compose -f docker-compose.prod.yml up -d --force-recreate web nginx
```

`--force-recreate` is required because compose only re-creates containers when it detects a change in the **image** or in the **compose file as parsed at run time**. Editing `nginx.conf` (a bind-mounted file) doesn't trigger that; without `--force-recreate`, nginx would keep reading the old config until the next image bump.

## 12. Two GitHub OAuth Apps (dev + prod)

GitHub OAuth apps have one callback URL per app. To make the GitHub button work both locally and on prod, register two OAuth apps under your GitHub account ([Settings → Developer settings → OAuth Apps](https://github.com/settings/developers)):

| App name              | Homepage URL                          | Callback URL                                                       |
|-----------------------|---------------------------------------|--------------------------------------------------------------------|
| `llm-portrait dev`    | `http://localhost:8000`               | `http://localhost:8000/accounts/github/login/callback/`            |
| `llm-portrait prod`   | `https://llm-portrait.gotdns.ch`      | `https://llm-portrait.gotdns.ch/accounts/github/login/callback/`   |

Put the dev creds into `.env` on your laptop, the prod creds into `.env` on the box.

After putting prod creds on the box, recreate web:

```bash
docker compose -f docker-compose.prod.yml up -d --force-recreate web
```

(`docker compose restart web` is **not enough** — it restarts the existing container with the env it was created with.)

## Known gaps

- **Compose / nginx files are not in CD.** They live on the box and are pushed manually with `scp`. Automating this is straightforward (an `scp` step in the CD workflow) but hasn't been wired up — see the "Known gap" section in [`development/ci-cd.md`](../development/ci-cd.md).
- **Mailhog on prod is a demo shortcut.** Real outbound mail would need an SMTP service (SES / Postmark / SendGrid). The code path is the same — just point `EMAIL_HOST` at the new server.
- **No automated DB backups.** For a graded internship project this is fine, but it's the obvious next thing if the project goes anywhere.
