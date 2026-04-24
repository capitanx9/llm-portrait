.PHONY: test test-cov

# Exit code 5 = "no tests collected" — treat as success while the test suite
# is still empty. Remove this fallback once the first real test is added.
test: ## Run pytest
	$(POETRY) run pytest || [ $$? -eq 5 ]

test-cov: ## Run pytest with coverage report
	$(POETRY) run pytest --cov=$(SRC) --cov-report=term-missing || [ $$? -eq 5 ]
