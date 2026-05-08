##@ OpenAPI

.PHONY: openapi-build openapi-validate

# We generate inside the web container so the schema reflects the exact
# Python deps (drf-spectacular, simplejwt) the running app uses, not whatever
# the host happens to have. Output goes to schemas/openapi.yaml — same folder
# as schemas/asyncapi.yaml, so both transports' specs live side by side.
openapi-build: ## Regenerate schemas/openapi.yaml from DRF views via drf-spectacular
	$(COMPOSE) exec -T web python manage.py spectacular --file schemas/openapi.yaml

openapi-validate: ## Generate schema with --validate; fails if it doesn't conform to OpenAPI 3
	$(COMPOSE) exec -T web python manage.py spectacular --validate --file /tmp/openapi-check.yaml
