.DEFAULT_GOAL := help

include makefiles/vars.mk
include makefiles/poetry.mk
include makefiles/lint.mk
include makefiles/test.mk
include makefiles/clean.mk

.PHONY: help check

help: ## Show this help message
	@printf "Available commands:\n\n"
	@awk 'BEGIN { FS = ":.*##" } \
		/^[a-zA-Z_-]+:.*##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 }' \
		$(MAKEFILE_LIST) | sort

check: lint test ## Run lint and tests (use before pushing)
