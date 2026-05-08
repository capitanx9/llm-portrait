##@ AsyncAPI

.PHONY: asyncapi-validate asyncapi-build

# We use the official asyncapi/cli docker image so the project doesn't grow
# an npm dependency. The image is pulled lazily on first run. We mount the
# `schemas/` folder as /work because that's where both the source YAML and
# the rendered HTML live — alongside future OpenAPI artefacts.
ASYNCAPI_DOCKER = docker run --rm -v $(CURDIR)/schemas:/work asyncapi/cli

asyncapi-validate: ## Validate schemas/asyncapi.yaml against the AsyncAPI 3 schema
	$(ASYNCAPI_DOCKER) validate /work/asyncapi.yaml

asyncapi-build: ## Regenerate schemas/asyncapi.html from schemas/asyncapi.yaml
	$(ASYNCAPI_DOCKER) generate fromTemplate /work/asyncapi.yaml @asyncapi/html-template \
		-o /work/_asyncapi-out --force-write \
		-p singleFile=true
	cp schemas/_asyncapi-out/index.html schemas/asyncapi.html
	rm -rf schemas/_asyncapi-out
