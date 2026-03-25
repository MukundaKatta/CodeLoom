.PHONY: install test lint format clean

install:
	pip install -e ".[dev]"

test:
	python -m pytest tests/ -v

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info .pytest_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} +
