.PHONY: ollama-pull

ollama-pull: ## Pull llama3.2:3b model into ollama
	$(COMPOSE) exec ollama ollama pull llama3.2:3b
