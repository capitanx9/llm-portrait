##@ Stack

.PHONY: up up-debug up-debug-wait down

up: ## Start dev stack (web + db)
	$(COMPOSE) up -d --build

up-debug: ## Start dev stack with debugpy on :5678 + HTTP body dump in logs
	DEBUGPY=1 LOG_HTTP_BODY=1 $(COMPOSE) up -d --build

up-debug-wait: ## Same as up-debug, but BLOCK until VS Code attaches (for startup-code breakpoints)
	DEBUGPY=1 DEBUGPY_WAIT=1 LOG_HTTP_BODY=1 $(COMPOSE) up -d --build

down: ## Stop dev stack
	$(COMPOSE) down
