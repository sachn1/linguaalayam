.PHONY: check lint format test ingest ingest-debug rag mcp

check:
	poetry run pre-commit run --all-files
	poetry run pytest --cov=linguaalayam --cov-fail-under=80

lint:
	poetry run ruff check .

format:
	poetry run ruff format .

test:
	poetry run pytest --cov=linguaalayam --cov-report=term-missing -q

ingest:
	poetry run ingest

ingest-debug:
	poetry run ingest corpus=debug

rag:
	poetry run rag 'rag.query=$(QUERY)' llm=nollm

mcp:
	poetry run mcp-server
