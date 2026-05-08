# CI / CD

How GitHub Actions takes a green PR all the way to a running container on EC2.

## Two workflows

| File                                            | What it does                                    |
|-------------------------------------------------|-------------------------------------------------|
| [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) | Lint, type-check, tests on every PR and push to `main`. |
| [`.github/workflows/cd.yml`](../../.github/workflows/cd.yml) | Build → push to ECR → SSH deploy → smoke test on success of CI on `main`. |

## CI

### Triggers

```yaml
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
```

A PR runs CI. A push to main (which only happens via squash-merge) re-runs CI on the merged result. The second run is what makes CD start.

### Jobs

Three parallel jobs:

| Job          | Tool       | Time |
|--------------|------------|------|
| `lint`       | ruff (check + format) | ~30s |
| `type-check` | mypy + django-stubs   | ~1m  |
| `test`       | pytest with Postgres + Redis services | ~1–2m |

All three jobs run on `ubuntu-latest`. They share a top-level `env` block that fakes out the Django settings:

```yaml
env:
  SECRET_KEY: ci-not-for-prod
  DEBUG: "False"
  ALLOWED_HOSTS: localhost
  DATABASE_URL: postgres://app:app@localhost:5432/llm_portrait
  CELERY_BROKER_URL: redis://localhost:6379/0
  REDIS_CACHE_URL: redis://localhost:6379/1
```

The lint and type-check jobs technically don't need the DB at all — but Django's settings module imports `dj_database_url`, which requires `DATABASE_URL` to be parseable. Faking it once at the top of the workflow is simpler than per-job env conditionals.

### Test job services

`test` declares Postgres and Redis as service containers:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    env:
      POSTGRES_DB: llm_portrait
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
    ports: ["5432:5432"]
    options: >-
      --health-cmd "pg_isready -U app -d llm_portrait"
      --health-interval 5s
      --health-timeout 3s
      --health-retries 10
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    options: >-
      --health-cmd "redis-cli ping"
      --health-interval 5s
      ...
```

GitHub waits for the healthchecks to go green before kicking off the steps. Once green, `pytest` runs against a fresh database every time.

Notably absent: **Ollama**. LLM tests mock it (`patch("app.users.views.generate_portrait", ...)`), so CI doesn't need a 2GB model image.

### Caching

Each job caches Poetry's virtualenv directory, keyed on `poetry.lock`:

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pypoetry
    key: poetry-${{ runner.os }}-${{ hashFiles('poetry.lock') }}
```

Subsequent CI runs reuse the cache and `poetry install` becomes a near no-op (~5 seconds).

## CD

### Trigger

```yaml
on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]
    branches: [main]
  workflow_dispatch:
```

CD only fires when a CI run on `main` finishes. The first job has an `if:` guard:

```yaml
if: ${{ github.event_name == 'workflow_dispatch'
        || github.event.workflow_run.conclusion == 'success' }}
```

This keeps red CI from accidentally rolling broken code to prod. `workflow_dispatch` is the manual escape hatch — run CD without an upstream CI (rare, used when the EC2 box needs a stack refresh after manual config changes).

### Permissions

```yaml
permissions:
  id-token: write
  contents: read
```

`id-token: write` is **mandatory** for OIDC. Without it the AWS-actions step can't request the federated token from GitHub.

### Jobs

#### 1. `build-and-push`

```yaml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}
    aws-region:    ${{ secrets.AWS_REGION }}

- uses: aws-actions/amazon-ecr-login@v2

- name: Compute image tag
  run: echo "tag=${GITHUB_SHA::7}" >> "$GITHUB_OUTPUT"

- name: Build image
  run: |
    docker build -f docker/Dockerfile \
      -t ${{ secrets.ECR_REGISTRY }}/${{ secrets.ECR_REPOSITORY }}:<sha> \
      -t ${{ secrets.ECR_REGISTRY }}/${{ secrets.ECR_REPOSITORY }}:latest \
      .

- name: Push image (sha tag)
- name: Push image (latest tag)
```

Two tags pushed — the short SHA gives auditable history; `:latest` is what the EC2 box pulls.

The OIDC dance happens in `aws-actions/configure-aws-credentials`: GitHub gives the runner a JWT signed by `token.actions.githubusercontent.com`, AWS STS exchanges it for short-lived credentials of the `llm-portrait-github-actions` role. No secret access keys involved.

#### 2. `deploy`

```yaml
- uses: appleboy/ssh-action@v1
  with:
    host: ${{ secrets.EC2_HOST }}
    username: ${{ secrets.EC2_USER }}
    key: ${{ secrets.EC2_SSH_KEY }}
    script: |
      cd /opt/llm-portrait
      aws ecr get-login-password --region ${{ secrets.AWS_REGION }} \
        | docker login --username AWS --password-stdin ${{ secrets.ECR_REGISTRY }}
      docker compose -f docker-compose.prod.yml pull
      docker compose -f docker-compose.prod.yml up -d
      docker image prune -f
```

The remote `aws ecr get-login-password` call works because the EC2 instance has the `llm-portrait-ec2` instance profile attached — read-only ECR access without explicit creds.

`docker compose pull` fetches the freshly-built `:latest` for `web` and `celery`. `up -d` recreates only the containers whose underlying image actually changed. `image prune` cleans up the previous image to keep the EBS disk from filling up.

#### 3. `smoke-test`

```yaml
- name: Wait for app to settle
  run: sleep 15

- name: Curl /health/        (legacy Lab 2 endpoint)   →  gunicorn, plain Django view
- name: Curl /api/health/    (DRF endpoint)            →  gunicorn, DRF router
- name: Curl /ws/docs/       (AsyncAPI viewer)         →  daphne, HTTP path
- name: WebSocket handshake  (anon → 403)              →  daphne, WS upgrade path
```

15-second sleep covers the gap between `docker compose up -d` returning and gunicorn actually accepting connections. Then four checks exercise four independent code paths:

- `/health/` is the Lab 2 plain-Django view. Proves gunicorn + nginx routing for `/` work.
- `/api/health/` is the same shape but through DRF + drf-spectacular. Proves the API stack survived the deploy, not just the legacy view.
- `/ws/docs/` is served by the **ws** container (daphne) over plain HTTP. Proves the ws service booted, nginx routes `/ws/*` to `ws:8001`, and the AsyncAPI HTML shipped with the image.
- The handshake check opens a real `wss://` connection to `/ws/chat/smoke/` with no JWT. Our `ChatConsumer` rejects unauthenticated clients before `accept()`, which Channels surfaces as HTTP 403 on the upgrade. A 403 here proves nginx forwarded the `Upgrade`/`Connection` headers (otherwise daphne would 400 the request), daphne routed the URL to our consumer, and the auth gate denies anon access. The HTTP path above and the WS upgrade path here use **different** code in nginx and daphne, so we want both green.

If the smoke-test fails, the deploy is **not** automatically rolled back. The previous container is already gone. The fix is to push another commit (or revert) and let CD re-run.

## GitHub secrets used

| Secret               | What it is                                                     |
|----------------------|----------------------------------------------------------------|
| `AWS_ROLE_TO_ASSUME` | ARN of `llm-portrait-github-actions` (OIDC role).              |
| `AWS_REGION`         | `eu-central-1`.                                                |
| `ECR_REGISTRY`       | `<account-id>.dkr.ecr.eu-central-1.amazonaws.com`.             |
| `ECR_REPOSITORY`     | `llm-portrait`.                                                |
| `EC2_HOST`           | Elastic IP, e.g. `63.183.30.218`.                              |
| `EC2_HOST_DOMAIN`    | `llm-portrait.gotdns.ch` (used by the smoke test).             |
| `EC2_USER`           | `ubuntu`.                                                      |
| `EC2_SSH_KEY`        | Private SSH key for the runner. Separate keypair from `strongbox` (the human-use one) — generated specifically for CI with no passphrase. |

Why a CI-specific SSH key: `appleboy/ssh-action` can't unlock a passphrase-protected key, so the developer's day-to-day key (with passphrase) doesn't work for CD. A second public key is appended to `~/.ssh/authorized_keys` on EC2; the matching private key sits in `EC2_SSH_KEY`. If the CI key is compromised, you remove that line from `authorized_keys`.

## Branch protection

`main` is protected (Settings → Branches → Branch protection rules):

- **Require a pull request before merging.**
- **Require status checks to pass before merging.** All three CI jobs are required.
- **Allow squash merging only.** Merge-commit and rebase-merge are disabled.
- **Do not allow force pushes.**
- **Do not allow deletions.**

There are **no required reviewers** — solo project. The CI gate plus the squash-only constraint together give the same protection a typical "1 approving review" rule would.

## Known gap

The CD pipeline only updates the **Docker image** for `web` and `celery`. Anything outside the image — `docker-compose.prod.yml`, `docker/nginx.conf`, `.env` — lives on the EC2 box and is updated manually with `scp` (see [`deployment/ec2.md`](../deployment/ec2.md)).

This is a deliberate trade-off: those files contain secrets (`.env`) or infrastructure choices that shouldn't live in the image. Automating them would mean either:

- **Bake them into the image** — bad, because `.env` is per-environment.
- **Add an `scp` step in the CD job** — fine, but the job would need write access to `/opt/llm-portrait/` over SSH and a way to store / fetch `.env` securely (AWS Secrets Manager / Parameter Store).

For the internship-scale project, doing it manually is acceptable. The first improvement when the project gains real users is to push compose + nginx via CD and pull `.env` from Parameter Store.
