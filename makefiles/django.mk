.PHONY: migrate makemigrations shell superuser runserver

migrate: ## Apply migrations inside the web container
	$(COMPOSE) exec web python manage.py migrate

makemigrations: ## Create new migrations from model changes
	$(COMPOSE) exec web python manage.py makemigrations

shell: ## Open a Django shell inside the web container
	$(COMPOSE) exec web python manage.py shell

superuser: ## Create a Django superuser
	$(COMPOSE) exec web python manage.py createsuperuser

runserver: ## Run Django dev server outside Docker (rare; needs local Postgres)
	$(POETRY) run python manage.py runserver
