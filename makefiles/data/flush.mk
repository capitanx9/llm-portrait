##@ Demo data (destructive)

.PHONY: flush-demo

flush-demo: ## Remove all seeded users / rooms / messages
	$(COMPOSE) exec web python manage.py flush_demo
