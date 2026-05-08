##@ Django · Users

.PHONY: superuser runserver

superuser: ## Create a Django superuser
	$(COMPOSE) exec web python manage.py createsuperuser

runserver: ## Run Django dev server outside Docker (rare; needs local Postgres)
	$(POETRY) run python manage.py runserver
