##@ Logs

.PHONY: logs logs-web logs-ws logs-celery logs-db logs-redis logs-mailhog logs-ollama

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
