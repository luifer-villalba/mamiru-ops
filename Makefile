SHELL := /bin/sh

COMPOSE ?= docker compose
PYTHON ?= python
MANAGE ?= $(PYTHON) manage.py
SERVICE ?= web

.DEFAULT_GOAL := help

.PHONY: help env build up down restart logs ps check shell bash migrate makemigrations superuser test collectstatic import local-run local-migrate local-makemigrations local-superuser local-test local-shell

help: ## Mostrar comandos disponibles
	@awk 'BEGIN {FS = ":.*##"; printf "\nUso: make <comando>\n\nComandos:\n"} /^[a-zA-Z0-9_-]+:.*##/ {printf "  %-22s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

env: ## Crear .env desde .env.example si no existe
	@echo "Revisando archivo .env..."
	@test -f .env || cp .env.example .env

build: ## Construir imagenes Docker
	@echo "Construyendo imagenes Docker..."
	$(COMPOSE) build

up: env ## Levantar servicios Docker en segundo plano
	@echo "Levantando servicios Docker..."
	$(COMPOSE) up --build -d

down: ## Detener servicios Docker y remover contenedores huerfanos
	@echo "Deteniendo servicios Docker..."
	$(COMPOSE) down --remove-orphans

restart: down up ## Reiniciar servicios Docker

logs: ## Ver logs de Docker en tiempo real
	@echo "Mostrando logs de Docker..."
	$(COMPOSE) logs -f

ps: ## Mostrar estado de servicios Docker
	@echo "Mostrando estado de servicios Docker..."
	$(COMPOSE) ps

check: ## Ejecutar chequeos de Django en un contenedor temporal
	@echo "Ejecutando chequeos de Django..."
	$(COMPOSE) run --rm --no-deps --entrypoint python $(SERVICE) manage.py check

shell: ## Abrir shell de Django en Docker
	@echo "Abriendo shell de Django en Docker..."
	$(COMPOSE) exec $(SERVICE) $(MANAGE) shell

bash: ## Abrir shell dentro del contenedor web
	@echo "Abriendo shell dentro del servicio Docker $(SERVICE)..."
	$(COMPOSE) exec $(SERVICE) sh

migrate: ## Ejecutar migraciones de Django en Docker
	@echo "Ejecutando migraciones de Django en Docker..."
	$(COMPOSE) exec $(SERVICE) $(MANAGE) migrate

makemigrations: ## Crear migraciones de Django en Docker
	@echo "Creando migraciones de Django en Docker..."
	$(COMPOSE) exec $(SERVICE) $(MANAGE) makemigrations

superuser: ## Crear superusuario de Django en Docker
	@echo "Creando superusuario de Django en Docker..."
	$(COMPOSE) exec $(SERVICE) $(MANAGE) createsuperuser

test: ## Ejecutar tests de Django en Docker
	@echo "Ejecutando tests de Django en Docker..."
	$(COMPOSE) exec $(SERVICE) $(MANAGE) test

collectstatic: ## Recolectar archivos estaticos en Docker
	@echo "Recolectando archivos estaticos en Docker..."
	$(COMPOSE) exec $(SERVICE) $(MANAGE) collectstatic --noinput

import: ## Importar CSV de stock en Docker. Uso: make import CSV=ruta/archivo.csv
	@echo "Importando CSV de stock en Docker..."
	@test -n "$(CSV)" || (echo "Falta CSV. Uso: make import CSV=ruta/archivo.csv" && exit 1)
	$(COMPOSE) exec $(SERVICE) $(MANAGE) import_mamiru_stock "$(CSV)"

local-run: env ## Levantar servidor de desarrollo local
	@echo "Levantando servidor de desarrollo local..."
	$(MANAGE) runserver

local-migrate: env ## Ejecutar migraciones localmente
	@echo "Ejecutando migraciones localmente..."
	$(MANAGE) migrate

local-makemigrations: env ## Crear migraciones localmente
	@echo "Creando migraciones localmente..."
	$(MANAGE) makemigrations

local-superuser: env ## Crear superusuario localmente
	@echo "Creando superusuario localmente..."
	$(MANAGE) createsuperuser

local-test: env ## Ejecutar tests localmente
	@echo "Ejecutando tests localmente..."
	$(MANAGE) test

local-shell: env ## Abrir shell de Django localmente
	@echo "Abriendo shell de Django localmente..."
	$(MANAGE) shell
