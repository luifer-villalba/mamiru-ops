SHELL := /bin/sh

COMPOSE ?= docker compose
PYTHON ?= python
MANAGE ?= $(PYTHON) manage.py
SERVICE ?= web

.DEFAULT_GOAL := help

.PHONY: help env build up down restart logs ps check shell bash migrate makemigrations superuser test collectstatic import local-run local-migrate local-makemigrations local-superuser local-test local-shell

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage: make <target>\n\nTargets:\n"} /^[a-zA-Z0-9_-]+:.*##/ {printf "  %-22s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

env: ## Create .env from .env.example if it does not exist
	@echo "Checking .env file..."
	@test -f .env || cp .env.example .env

build: ## Build Docker images
	@echo "Building Docker images..."
	$(COMPOSE) build

up: env ## Start Docker services in the background
	@echo "Starting Docker services..."
	$(COMPOSE) up --build -d

down: ## Stop Docker services and remove orphan containers
	@echo "Stopping Docker services..."
	$(COMPOSE) down --remove-orphans

restart: down up ## Restart Docker services

logs: ## Follow Docker logs
	@echo "Following Docker logs..."
	$(COMPOSE) logs -f

ps: ## Show Docker services status
	@echo "Showing Docker services status..."
	$(COMPOSE) ps

check: ## Run Django system checks in a temporary Docker container
	@echo "Running Django system checks..."
	$(COMPOSE) run --rm --no-deps --entrypoint python $(SERVICE) manage.py check

shell: ## Open Django shell in Docker
	@echo "Opening Django shell in Docker..."
	$(COMPOSE) exec $(SERVICE) $(MANAGE) shell

bash: ## Open a shell inside the Docker web container
	@echo "Opening shell inside Docker service $(SERVICE)..."
	$(COMPOSE) exec $(SERVICE) sh

migrate: ## Run Django migrations in Docker
	@echo "Running Django migrations in Docker..."
	$(COMPOSE) exec $(SERVICE) $(MANAGE) migrate

makemigrations: ## Create Django migrations in Docker
	@echo "Creating Django migrations in Docker..."
	$(COMPOSE) exec $(SERVICE) $(MANAGE) makemigrations

superuser: ## Create Django superuser in Docker
	@echo "Creating Django superuser in Docker..."
	$(COMPOSE) exec $(SERVICE) $(MANAGE) createsuperuser

test: ## Run Django tests in Docker
	@echo "Running Django tests in Docker..."
	$(COMPOSE) exec $(SERVICE) $(MANAGE) test

collectstatic: ## Collect static files in Docker
	@echo "Collecting static files in Docker..."
	$(COMPOSE) exec $(SERVICE) $(MANAGE) collectstatic --noinput

import: ## Import stock CSV in Docker. Usage: make import CSV=path/to/file.csv
	@echo "Importing stock CSV in Docker..."
	@test -n "$(CSV)" || (echo "Missing CSV. Usage: make import CSV=path/to/file.csv" && exit 1)
	$(COMPOSE) exec $(SERVICE) $(MANAGE) import_mamiru_stock "$(CSV)"

local-run: env ## Run Django development server locally
	@echo "Starting Django development server locally..."
	$(MANAGE) runserver

local-migrate: env ## Run Django migrations locally
	@echo "Running Django migrations locally..."
	$(MANAGE) migrate

local-makemigrations: env ## Create Django migrations locally
	@echo "Creating Django migrations locally..."
	$(MANAGE) makemigrations

local-superuser: env ## Create Django superuser locally
	@echo "Creating Django superuser locally..."
	$(MANAGE) createsuperuser

local-test: env ## Run Django tests locally
	@echo "Running Django tests locally..."
	$(MANAGE) test

local-shell: env ## Open Django shell locally
	@echo "Opening Django shell locally..."
	$(MANAGE) shell
