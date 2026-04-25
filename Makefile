.PHONY: install test lint run clean

install:
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/

run:
	python -m voice_agent.app

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
