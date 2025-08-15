.PHONY: help install install-dev test test-cov lint format type-check security clean build docs serve run

# Default target
help:  ## Show this help message
	@echo "MusicWeb Development Commands"
	@echo "============================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Installation targets
install:  ## Install production dependencies
	pip install -e .

install-dev:  ## Install development dependencies
	pip install -e ".[dev,test,docs]"
	pre-commit install

# Testing targets
test:  ## Run tests
	pytest tests/ -v

test-cov:  ## Run tests with coverage
	pytest tests/ --cov=src/musicweb --cov-report=html --cov-report=term-missing --cov-report=xml

test-watch:  ## Run tests in watch mode
	pytest-watch tests/ src/

# Code quality targets
lint:  ## Run linting
	flake8 src/ tests/
	bandit -r src/musicweb/

format:  ## Format code
	black src/ tests/
	isort src/ tests/

format-check:  ## Check code formatting
	black --check src/ tests/
	isort --check-only src/ tests/

type-check:  ## Run type checking
	mypy src/musicweb/

# Security targets
security:  ## Run security scans
	bandit -r src/musicweb/ -f json -o bandit-report.json
	safety check --json --output safety-report.json || true

security-full:  ## Run comprehensive security scan
	$(MAKE) security
	docker run --rm -v $(PWD):/src aquasecurity/trivy fs /src

# Quality checks (run all)
check:  ## Run all quality checks
	$(MAKE) format-check
	$(MAKE) lint
	$(MAKE) type-check
	$(MAKE) security
	$(MAKE) test-cov

# Pre-commit
pre-commit:  ## Run pre-commit hooks
	pre-commit run --all-files

pre-commit-update:  ## Update pre-commit hooks
	pre-commit autoupdate

# Clean targets
clean:  ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

clean-logs:  ## Clean log files
	rm -rf logs/
	rm -f *.log

# Build targets
build:  ## Build package
	python -m build

build-docker:  ## Build Docker image
	docker build -t musicweb:latest .

# Documentation targets
docs:  ## Build documentation
	cd docs && make html

docs-serve:  ## Serve documentation locally
	cd docs && make livehtml

docs-clean:  ## Clean documentation build
	cd docs && make clean

# Development server targets
serve:  ## Start development web server
	streamlit run src/musicweb/web/app.py

serve-prod:  ## Start production web server
	streamlit run src/musicweb/web/app.py --server.port 8501 --server.address 0.0.0.0

run:  ## Run CLI application
	musicweb --help

# Release targets
version-patch:  ## Bump patch version
	bump2version patch

version-minor:  ## Bump minor version
	bump2version minor

version-major:  ## Bump major version
	bump2version major

release:  ## Create release (after version bump)
	git push --tags
	git push origin main
	python -m build
	twine check dist/*

release-test:  ## Release to test PyPI
	twine upload --repository testpypi dist/*

release-prod:  ## Release to production PyPI
	twine upload dist/*

# Docker targets
docker-build:  ## Build Docker image
	docker build -t musicweb:latest .

docker-run:  ## Run Docker container
	docker run -p 8501:8501 musicweb:latest

docker-compose-up:  ## Start with docker-compose
	docker-compose up -d

docker-compose-down:  ## Stop docker-compose
	docker-compose down

# Database targets (if applicable)
db-init:  ## Initialize database
	python -c "from musicweb.utils.database import init_db; init_db()"

db-migrate:  ## Run database migrations
	python -c "from musicweb.utils.database import migrate_db; migrate_db()"

# Environment setup
env-dev:  ## Set up development environment
	python -m venv venv
	. venv/bin/activate && pip install -e ".[dev,test,docs]"
	. venv/bin/activate && pre-commit install
	@echo "Development environment set up. Activate with: source venv/bin/activate"

env-check:  ## Check environment setup
	python --version
	pip list | grep musicweb || echo "MusicWeb not installed"
	pre-commit --version || echo "pre-commit not installed"

# Performance targets
profile:  ## Run performance profiling
	python -m cProfile -s cumtime scripts/profile_app.py

benchmark:  ## Run benchmarks
	python scripts/benchmark.py

# Monitoring
logs:  ## Show recent logs
	tail -f logs/musicweb.log

logs-error:  ## Show recent error logs
	tail -f logs/musicweb_errors.log

status:  ## Show application status
	@echo "Checking application status..."
	@python -c "import requests; print('Web app:', requests.get('http://localhost:8501').status_code)" 2>/dev/null || echo "Web app: Not running"

# CI/CD simulation
ci-local:  ## Simulate CI pipeline locally
	$(MAKE) clean
	$(MAKE) install-dev
	$(MAKE) check
	$(MAKE) build
	@echo "✅ CI pipeline simulation completed successfully"