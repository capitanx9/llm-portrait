.PHONY: up down logs build bash

COMPOSE := docker compose -f docker-compose.dev.yml

up: ## Start dev stack (web + db)
	$(COMPOSE) up -d --build

down: ## Stop dev stack
	$(COMPOSE) down

logs: ## Tail compose logs
	$(COMPOSE) logs -f

build: ## Rebuild web image
	$(COMPOSE) build web

bash: ## Open a shell in the web container
	$(COMPOSE) exec web bash
