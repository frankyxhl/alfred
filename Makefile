.PHONY: test lint typecheck check install

test:
	.venv/bin/pytest -v --tb=short

lint:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .

typecheck:
	.venv/bin/pyright src/

check: lint typecheck test

install:
	uv venv
	uv pip install -e .
	uv pip install pytest ruff pyright build
