# llm-portrait

Django web application that generates a tarot-style psychological portrait of a user via a local LLM (Llama3.2). Users register, fill in their tarot-themed profile (arcana, element, shadow, quest, curse, totem, forbidden magic), pick friends, and get an AI-generated description that takes the friends' arcanas into account.

Production deploy: <https://llm-portrait.gotdns.ch>

**Stack:** Python 3.12, Django 5.2, PostgreSQL 16, Redis 7, Celery, LangChain + Ollama (Llama3.2:3b), Bootstrap 5, Docker Compose, Nginx + Gunicorn, AWS EC2 + ECR, GitHub Actions.

## Documentation

The full documentation lives under [`docs/`](./docs/):

- [Overview](./docs/overview.md) — what the project is and what users can do.
- [Architecture](./docs/architecture.md) — services, diagrams, data flow.
- Deployment: [local](./docs/deployment/local.md), [AWS EC2](./docs/deployment/ec2.md).
- Development: [workflow](./docs/development/workflow.md), [tooling](./docs/development/tooling.md), [testing](./docs/development/testing.md), [CI/CD](./docs/development/ci-cd.md).
