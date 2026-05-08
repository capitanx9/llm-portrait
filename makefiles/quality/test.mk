##@ Tests

.PHONY: test test-cov

test: ## Run pytest inside the web container (needs `make up` first)
	$(COMPOSE) exec web python -m pytest

test-cov: ## Run pytest with coverage report inside the web container
	$(COMPOSE) exec web python -m pytest --cov=$(SRC) --cov-report=term-missing
