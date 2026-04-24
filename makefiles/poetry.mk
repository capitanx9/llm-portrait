.PHONY: install info lock

install: ## Install dependencies and pre-commit hooks
	$(POETRY) install
	$(POETRY) run pre-commit install

info: ## Show poetry env info
	$(POETRY) env info

lock: ## Refresh poetry.lock
	$(POETRY) lock
