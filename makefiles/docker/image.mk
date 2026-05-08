##@ Image

.PHONY: build bash

build: ## Rebuild web image
	$(COMPOSE) build web

bash: ## Open a shell in the web container
	$(COMPOSE) exec web bash
