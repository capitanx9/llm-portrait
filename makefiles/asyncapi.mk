.PHONY: asyncapi-validate asyncapi-build

# We use the official asyncapi/cli docker image so the project doesn't grow
# an npm dependency. The image is pulled lazily on first run.
ASYNCAPI_DOCKER = docker run --rm -v $(CURDIR)/docs:/work asyncapi/cli

asyncapi-validate: ## Validate docs/asyncapi.yaml against the AsyncAPI 3 schema
	$(ASYNCAPI_DOCKER) validate /work/asyncapi.yaml

asyncapi-build: ## Regenerate docs/asyncapi.html from docs/asyncapi.yaml
	$(ASYNCAPI_DOCKER) generate fromTemplate /work/asyncapi.yaml @asyncapi/html-template \
		-o /work/_asyncapi-out --force-write \
		-p singleFile=true
	cp docs/_asyncapi-out/index.html docs/asyncapi.html
	rm -rf docs/_asyncapi-out
