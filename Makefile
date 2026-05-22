# ==============================================================================
# Installation & Setup
# ==============================================================================

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