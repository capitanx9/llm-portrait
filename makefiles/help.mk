##@ Meta

.PHONY: help check

help: ## Show this help message
	@awk 'BEGIN { FS = ":.*##"; section = "" } \
		/^##@/ { section = substr($$0, 5); printf "\n\033[1m%s\033[0m\n", section; next } \
		/^[a-zA-Z_-]+:.*##/ { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' \
		$(MAKEFILE_LIST)

check: lint test ## Run lint and tests (use before pushing)
