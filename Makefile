.PHONY: install test lint run

install:
	python3 -m venv .venv
	.venv/bin/pip install -e ".[dev]"

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check src tests

run:
	.venv/bin/python -m issuebot
