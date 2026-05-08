##@ Stack reset

.PHONY: reset-db

reset-db: ## Drop volumes (pgdata, ollama_data) and rebuild — DESTRUCTIVE
	@echo ">>> WARNING: this removes pgdata + ollama_data volumes. Ctrl-C within 3s to cancel."
	@sleep 3
	$(COMPOSE) down -v
	$(COMPOSE) up -d --build
	$(MAKE) migrate
