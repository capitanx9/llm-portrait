PROJECT_NAME := $(shell basename `pwd`)
PY_SRC := src/$(subst -,_,$(PROJECT_NAME))
POETRY := poetry

install:
	$(POETRY) install

run:
	$(POETRY) run python -m $(PY_SRC).main

test:
	$(POETRY) run pytest -v --disable-warnings

freeze:
	$(POETRY) lock --no-update
	$(POETRY) export -f requirements.txt --output requirements.txt

clean:
	rm -rf __pycache__ .mypy_cache .pytest_cache dist build *.egg-info
	find . -name "*.pyc" -delete
	@echo "Clean done."

info:
	@$(POETRY) env info
