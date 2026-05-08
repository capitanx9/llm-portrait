##@ Django · DB

.PHONY: migrate makemigrations shell

migrate: ## Apply migrations inside the web container
	$(COMPOSE) exec web python manage.py migrate

makemigrations: ## Create new migrations from model changes
	$(COMPOSE) exec web python manage.py makemigrations

shell: ## Open a Django shell inside the web container
	$(COMPOSE) exec web python manage.py shell
