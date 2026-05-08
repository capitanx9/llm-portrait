##@ Lint & format

.PHONY: lint format mypy

lint: ## Run ruff check and mypy
	$(POETRY) run ruff check .
	$(POETRY) run ruff format --check .
	$(POETRY) run mypy $(SRC)

format: ## Auto-format code with ruff
	$(POETRY) run ruff format .
	$(POETRY) run ruff check --fix .

mypy: ## Run mypy only
	$(POETRY) run mypy $(SRC)
