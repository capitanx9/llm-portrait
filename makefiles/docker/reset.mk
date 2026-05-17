##@ Stack reset

.PHONY: reset-db reset-ollama reset-redis reset-all

reset-db: ## Drop pgdata only and re-migrate — keeps Ollama model + Redis state
	@echo ">>> WARNING: this wipes the Postgres volume. Ctrl-C within 3s to cancel."
	@sleep 3
	$(COMPOSE) rm -fsv db
	docker volume rm llm-portrait_pgdata 2>/dev/null || true
	$(COMPOSE) up -d db
	$(MAKE) migrate

reset-ollama: ## Drop ollama_data only — re-pulls llama3.2:3b on next AI call (~2 GB)
	@echo ">>> WARNING: this wipes the Llama model. Next AI call will re-pull ~2 GB. Ctrl-C within 3s to cancel."
	@sleep 3
	$(COMPOSE) rm -fsv ollama
	docker volume rm llm-portrait_ollama_data 2>/dev/null || true
	$(COMPOSE) up -d ollama

reset-redis: ## Restart Redis container — flushes the in-memory cache, channel layer, and Celery broker queue
	@echo ">>> WARNING: this drops everything in Redis (cache, Channels groups, Celery queue). Ctrl-C within 3s to cancel."
	@sleep 3
	$(COMPOSE) restart redis

reset-all: ## Drop ALL volumes (pgdata + ollama_data) and rebuild — re-pulls the LLM model
	@echo ">>> WARNING: this removes pgdata + ollama_data volumes (you will re-pull llama3.2:3b). Ctrl-C within 3s to cancel."
	@sleep 3
	$(COMPOSE) down -v
	$(COMPOSE) up -d --build
	$(MAKE) migrate
