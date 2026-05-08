.DEFAULT_GOAL := help

include makefiles/vars.mk
include makefiles/help.mk
include makefiles/docker/lifecycle.mk
include makefiles/docker/logs.mk
include makefiles/docker/image.mk
include makefiles/docker/reset.mk
include makefiles/django/db.mk
include makefiles/django/users.mk
include makefiles/data/seed.mk
include makefiles/data/flush.mk
include makefiles/quality/lint.mk
include makefiles/quality/test.mk
include makefiles/tooling/poetry.mk
include makefiles/tooling/llm.mk
include makefiles/tooling/asyncapi.mk
include makefiles/tooling/openapi.mk
include makefiles/clean.mk
