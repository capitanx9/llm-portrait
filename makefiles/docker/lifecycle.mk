##@ Stack

.PHONY: up up-debug up-debug-wait down

up: ## Start dev stack (web + db)
	$(COMPOSE) up -d --build

up-debug: ## Start dev stack with debugpy listening on :5678
	DEBUGPY=1 $(COMPOSE) up -d --build

up-debug-wait: ## Start dev stack and BLOCK until VS Code attaches to debugpy
	DEBUGPY=1 DEBUGPY_WAIT=1 $(COMPOSE) up -d --build

down: ## Stop dev stack
	$(COMPOSE) down
