# Overview

## Goal

`llm-portrait` is the second of three internship practicals. The brief asks for a Django application that:

1. Defines `User`, `UserProfile`, and `UserFriends` models with non-trivial profile fields and exposes them in the admin.
2. Implements signin / signup via three different paths: classic basic auth (username + email + password) with a welcome email, GitHub OAuth, and password reset over email.
3. Generates an AI description for a user's profile via a local LLM, with a per-user rate limit.
4. Ships everything as a `docker-compose` deployable bundle.

The project's flavour is tarot: instead of plain "interests" / "bio" fields, the profile is structured around tarot archetypes — major arcana, element, shadow, quest, curse, totem, forbidden magic. Friends contribute their own arcanas to the prompt, so the generated portrait reads each user inside their social context.

## What users can do

- **Sign up** with username, email, and password — or sign in with **GitHub OAuth**.
- **Reset their password** via email (delivered through Celery → Mailhog in dev / SMTP in prod).
- **Edit their tarot profile** at `/portrait/`: arcana (22 majors, Russian labels), element (fire / water / air / earth), and free-text fields for shadow, quest, curse, totem, forbidden magic, plus `age` and `location`.
- **Manage friends** from the same page: a list of all other users with one-click "Add" / "In friends" toggle. Friendships are symmetric (a `post_save` signal mirrors the row), so adding back is automatic.
- **Generate an AI portrait** by clicking the button at the bottom of the profile. The LLM reads all the user's tarot fields plus the arcanas of their friends, and writes a 100–150 word psychological description. Generation is rate-limited to 2 requests per minute per user (configurable).

The Russian-speaking UI is intentional: the tarot vocabulary (Маг, Жрица, Колесница, Огонь, …) is more idiomatic in Russian, and the LLM is prompted in Russian as well.

## Stack at a glance

- **Backend:** Django 5.2, Python 3.12.
- **Auth:** [django-allauth](https://docs.allauth.org) for both password-based auth and GitHub OAuth.
- **Async / email:** Celery 5 with Redis broker; Mailhog as an SMTP sink in dev; the same SMTP target on prod (intentionally simple — switching to SES/Postmark is one env change).
- **LLM:** [Ollama](https://ollama.ai) running [Llama3.2:3b](https://ollama.ai/library/llama3.2) locally; [LangChain](https://python.langchain.com) for prompt templating.
- **Database:** PostgreSQL 16.
- **Cache / rate limit:** Redis 7 via [django-redis](https://github.com/jazzband/django-redis); [django-ratelimit](https://django-ratelimit.readthedocs.io) for the LLM endpoint.
- **Frontend:** server-rendered Django templates, Bootstrap 5 + Bootstrap Icons via CDN. A small inline JS handles the password show/hide toggle and the loading spinner on the LLM button.
- **Containers:** Docker Compose. Two compose files: `docker-compose.dev.yml` for development and `docker-compose.prod.yml` for the EC2 deploy.
- **TLS / domain:** Let's Encrypt via certbot, NoIP DDNS domain `llm-portrait.gotdns.ch` pointing at an AWS Elastic IP.
- **Hosting:** AWS EC2 (`t3a.large`, Ubuntu 24.04) in `eu-central-1`. Container images are stored in AWS ECR.
- **CI/CD:** GitHub Actions. CI runs ruff, mypy, and pytest. CD authenticates to AWS via OIDC, builds the image, pushes to ECR, SSHs into EC2, and rolls the stack.

## Where to read next

- New to the project? Start with [architecture](./architecture.md) for the high-level diagram.
- Want to run it on your machine? See [local deployment](./deployment/local.md).
- Want to reproduce the production setup? See [EC2 deployment](./deployment/ec2.md).
- Curious about how the project is built and shipped? See the [development](./development/workflow.md) section.
