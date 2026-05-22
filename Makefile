# ==============================================================================
# Installation & Setup
# ==============================================================================

# Проверяем, существует ли файл .env, и если да — загружаем его
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

LOAD_ENV = set -a; [ ! -f .env ] || . ./.env; set +a

# Install dependencies using uv package manager
install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/install.sh | sh; source $$HOME/.local/bin/env; }
	uv sync

# ==============================================================================
# Local Development
# ==============================================================================

# Launch local server
run:
	@echo "==============================================================================="
	@echo "| 🚀 Starting Lazy Stellar CLI...                                             |"
	@echo "==============================================================================="
	uv run python -m entrypoints.cli

# Launch browser chat UI for local agent debugging
web:
	@echo "==============================================================================="
	@echo "| Starting Lazy Stellar Web UI at http://127.0.0.1:7932                       |"
	@echo "==============================================================================="
	@$(LOAD_ENV); test -n "$$OPENROUTER_API_KEY" || { echo "OPENROUTER_API_KEY is required for the default model. Set it or change LAZY_STELLAR_MODEL."; exit 1; }
	$(LOAD_ENV); uv run uvicorn entrypoints.web:app --host 127.0.0.1 --port 7932

# Launch browser chat UI with Pydantic AI's deterministic test model
web-fake:
	@echo "==============================================================================="
	@echo "| Starting Lazy Stellar Web UI with test model at http://127.0.0.1:7932       |"
	@echo "==============================================================================="
	$(LOAD_ENV); LAZY_STELLAR_MODEL=test uv run uvicorn entrypoints.web:app --host 127.0.0.1 --port 7932

# Stop any local Lazy Stellar web server holding the development port
stop:
	@pids=$$(lsof -tiTCP:7932 -sTCP:LISTEN 2>/dev/null); \
	if [ -n "$$pids" ]; then \
		echo "Stopping Lazy Stellar process(es) on port 7932: $$pids"; \
		kill $$pids; \
	else \
		echo "No Lazy Stellar web server is listening on port 7932."; \
	fi

# ==============================================================================
# Testing & Code Quality
# ==============================================================================

# Run unit and integration tests
test:
	uv sync --dev
	uv run pytest tests/unit tests/integration

# Run code quality checks (ruff, mypy)
lint:
	uv sync --all-extras --dev
	uv run ruff check .
	uv run ruff format . --check
	uv run mypy .
