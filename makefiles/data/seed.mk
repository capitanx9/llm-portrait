##@ Demo data

.PHONY: seed-users seed-rooms seed-messages seed-all

seed-users: ## Create five demo chat users (idempotent)
	$(COMPOSE) exec web python manage.py seed_users

seed-rooms: ## Create demo rooms general/random/ai-help (idempotent)
	$(COMPOSE) exec web python manage.py seed_rooms

seed-messages: ## Re-seed demo messages in demo rooms (replaces existing)
	$(COMPOSE) exec web python manage.py seed_messages

seed-all: ## seed-users + seed-rooms + seed-messages
	$(COMPOSE) exec web python manage.py seed_all
