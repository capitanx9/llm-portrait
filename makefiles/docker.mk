.PHONY: up up-debug up-debug-wait down logs logs-web logs-ws logs-celery logs-db logs-redis logs-mailhog logs-ollama build bash

COMPOSE := docker compose -f docker-compose.dev.yml

up: ## Start dev stack (web + db)
	$(COMPOSE) up -d --build

up-debug: ## Start dev stack with debugpy listening on :5678
	DEBUGPY=1 $(COMPOSE) up -d --build

up-debug-wait: ## Start dev stack and BLOCK until VS Code attaches to debugpy
	DEBUGPY=1 DEBUGPY_WAIT=1 $(COMPOSE) up -d --build

down: ## Stop dev stack
	$(COMPOSE) down

logs: ## Tail logs of every service (noisy; prefer logs-<service> while debugging)
	$(COMPOSE) logs -f

logs-web: ## Tail web (gunicorn / Django) logs
	$(COMPOSE) logs -f web

logs-ws: ## Tail ws (daphne / Channels) logs
	$(COMPOSE) logs -f ws

logs-celery: ## Tail celery worker logs
	$(COMPOSE) logs -f celery

logs-db: ## Tail Postgres logs
	$(COMPOSE) logs -f db

logs-redis: ## Tail Redis logs
	$(COMPOSE) logs -f redis

logs-mailhog: ## Tail Mailhog logs (incoming SMTP / API events)
	$(COMPOSE) logs -f mailhog

logs-ollama: ## Tail Ollama logs (model loading / inference)
	$(COMPOSE) logs -f ollama

build: ## Rebuild web image
	$(COMPOSE) build web

bash: ## Open a shell in the web container
	$(COMPOSE) exec web bash
