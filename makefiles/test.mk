.PHONY: test test-cov

test: ## Run pytest
	$(POETRY) run pytest

test-cov: ## Run pytest with coverage report
	$(POETRY) run pytest --cov=$(SRC) --cov-report=term-missing
