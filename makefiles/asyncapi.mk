.PHONY: asyncapi-validate asyncapi-build

# We use the official asyncapi/cli docker image so the project doesn't grow
# an npm dependency. The image is pulled lazily on first run. We mount the
# `docs/api/ws/` folder as /work because that's where both the source YAML
# and the rendered HTML live — the spec is a "WS API artefact", not a
# free-floating doc file.
ASYNCAPI_DOCKER = docker run --rm -v $(CURDIR)/docs/api/ws:/work asyncapi/cli

asyncapi-validate: ## Validate docs/api/ws/asyncapi.yaml against the AsyncAPI 3 schema
	$(ASYNCAPI_DOCKER) validate /work/asyncapi.yaml

asyncapi-build: ## Regenerate docs/api/ws/asyncapi.html from docs/api/ws/asyncapi.yaml
	$(ASYNCAPI_DOCKER) generate fromTemplate /work/asyncapi.yaml @asyncapi/html-template \
		-o /work/_asyncapi-out --force-write \
		-p singleFile=true
	cp docs/api/ws/_asyncapi-out/index.html docs/api/ws/asyncapi.html
	rm -rf docs/api/ws/_asyncapi-out
