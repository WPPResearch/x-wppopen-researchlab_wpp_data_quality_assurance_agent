.PHONY: help install setup lint format test eval run web docker-build docker-run pre-commit clean check

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install project dependencies
	uv sync --python 3.13

setup: install ## Full setup: install deps, pre-commit hooks, create .env
	pre-commit install
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env from .env.example — fill in your values"; fi

lint: ## Run linting with ruff
	uv run ruff check .

format: ## Auto-format code with ruff
	uv run ruff format .

test: ## Run unit tests
	uv run pytest tests/

eval: ## Run agent evaluations
	uv run pytest eval/

run: ## Run the agent in CLI mode
	uv run adk run data_science

web: ## Run the agent with ADK web UI
	./scripts/run_web.sh

docker-build: ## Build Docker image
	docker build -t data-science-agent .

docker-run: ## Run the agent in Docker
	docker run --env-file .env -p 8080:8080 data-science-agent

pre-commit: ## Run pre-commit hooks on all files
	uv run pre-commit run --all-files

check: lint test ## Run lint + tests (CI equivalent)

clean: ## Remove build artifacts and caches
	rm -rf __pycache__ .pytest_cache .ruff_cache *.egg-info build/
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
