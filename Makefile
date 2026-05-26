SHELL := /bin/sh

COMPOSE ?= docker compose
PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON ?= $(VENV)/bin/python
VENV_STAMP ?= $(VENV)/.installed
MANAGE ?= $(PYTHON) manage.py
LOCAL_MANAGE ?= $(VENV_PYTHON) manage.py
LOCAL_RUFF ?= $(VENV)/bin/ruff
LOCAL_PYTEST ?= $(VENV)/bin/pytest
SERVICE ?= web
SEED_FILE ?= data/stock.csv
DB_VOLUME ?= mamiru-ops_postgres_data
RUNSERVER_ADDR ?= 127.0.0.1:8000
SQLITE_DATABASE_URL ?= sqlite:////tmp/mamiru-ops-dev.sqlite3
POSTGRES_HOST_PORT ?= 5433
LOCAL_DATABASE_URL ?= postgres://mamiru:mamiru@127.0.0.1:$(POSTGRES_HOST_PORT)/mamiru
LOCAL_STATIC_ROOT ?= /tmp/mamiru-ops-staticfiles
APP_URL ?= http://localhost:8000
ADMIN_URL ?= $(APP_URL)/
PRODUCTS_ADMIN_URL ?= $(APP_URL)/admin/catalog/product/
PURCHASE_HISTORY_URL ?= $(APP_URL)/admin/catalog/purchaseorder/
API_URL ?= $(APP_URL)/api/
API_PRODUCTS_URL ?= $(APP_URL)/api/products/

.DEFAULT_GOAL := help

.PHONY: help links env build up down restart logs ps check shell bash migrate makemigrations superuser test collectstatic import seed reset-db venv runserver sqlite-runserver local-run local-migrate local-makemigrations local-superuser local-test local-shell lint format lint-fix pytest pytest-cov

help: ## Mostrar comandos disponibles
	@awk 'BEGIN {FS = ":.*##"; printf "\nUso: make <comando>\n\nComandos:\n"} /^[a-zA-Z0-9_-]+:.*##/ {printf "  %-22s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Links utiles:"
	@echo "  App/Admin:           $(ADMIN_URL)"
	@echo "  Historial compras:   $(PURCHASE_HISTORY_URL)"
	@echo "  Productos admin:     $(PRODUCTS_ADMIN_URL)"
	@echo "  API:                 $(API_URL)"
	@echo ""
	@echo "Tip: podes cambiar el host con APP_URL=http://127.0.0.1:8000 make links"

links: ## Mostrar links utiles del entorno local
	@echo "Mamiru Ops - links locales"
	@echo "  App/Admin:           $(ADMIN_URL)"
	@echo "  Historial compras:   $(PURCHASE_HISTORY_URL)"
	@echo "  Productos admin:     $(PRODUCTS_ADMIN_URL)"
	@echo "  API:                 $(API_URL)"
	@echo "  API productos:       $(API_PRODUCTS_URL)"

env: ## Crear .env desde .env.example si no existe
	@echo "Revisando archivo .env..."
	@test -f .env || cp .env.example .env
	@echo ".env listo. Si necesitas tocar credenciales locales, edita .env"

build: ## Construir imagenes Docker
	@echo "Construyendo imagenes Docker..."
	$(COMPOSE) build
	@echo "Imagenes listas. Siguiente paso habitual: make up"

up: env ## Levantar servicios Docker en segundo plano
	@echo "Levantando servicios Docker..."
	$(COMPOSE) up --build -d
	@echo "Servicios arriba."
	@echo "  Admin:         $(ADMIN_URL)"
	@echo "  API:           $(API_URL)"
	@echo "Para ver logs: make logs"

down: ## Detener servicios Docker y remover contenedores huerfanos
	@echo "Deteniendo servicios Docker..."
	$(COMPOSE) down --remove-orphans
	@echo "Servicios detenidos."

restart: down up ## Reiniciar servicios Docker

logs: ## Ver logs de Docker en tiempo real
	@echo "Mostrando logs de Docker..."
	@echo "Admin local: $(ADMIN_URL)"
	$(COMPOSE) logs -f

ps: ## Mostrar estado de servicios Docker
	@echo "Mostrando estado de servicios Docker..."
	$(COMPOSE) ps
	@echo "Links rapidos: make links"

check: ## Ejecutar chequeos de Django en un contenedor temporal
	@echo "Ejecutando chequeos de Django..."
	$(COMPOSE) run --rm --no-deps --entrypoint python $(SERVICE) manage.py check
	@echo "Django check OK."

shell: ## Abrir shell de Django en Docker
	@echo "Abriendo shell de Django en Docker..."
	@echo "Modelo util: from catalog.models import Product, PurchaseOrder"
	$(COMPOSE) exec $(SERVICE) $(MANAGE) shell

bash: ## Abrir shell dentro del contenedor web
	@echo "Abriendo shell dentro del servicio Docker $(SERVICE)..."
	$(COMPOSE) exec $(SERVICE) sh

migrate: ## Ejecutar migraciones de Django en Docker
	@echo "Ejecutando migraciones de Django en Docker..."
	$(COMPOSE) exec $(SERVICE) $(MANAGE) migrate
	@echo "Migraciones aplicadas. Admin: $(ADMIN_URL)"

makemigrations: ## Crear migraciones de Django en Docker
	@echo "Creando migraciones de Django en Docker..."
	$(COMPOSE) exec $(SERVICE) $(MANAGE) makemigrations
	@echo "Migraciones creadas. Revisalas con: git diff catalog/migrations"

superuser: ## Crear superusuario de Django en Docker
	@echo "Creando superusuario de Django en Docker..."
	$(COMPOSE) exec $(SERVICE) $(MANAGE) createsuperuser
	@echo "Cuando termines, entra al admin: $(ADMIN_URL)"

test: ## Ejecutar tests de Django en Docker
	@echo "Ejecutando tests de Django en Docker..."
	$(COMPOSE) exec $(SERVICE) $(MANAGE) test
	@echo "Tests OK."

collectstatic: ## Recolectar archivos estaticos en Docker
	@echo "Recolectando archivos estaticos en Docker..."
	$(COMPOSE) exec $(SERVICE) $(MANAGE) collectstatic --noinput
	@echo "Static listo para servir con WhiteNoise."

import: ## Importar CSV de stock en Docker. Uso: make import CSV=ruta/archivo.csv
	@echo "Importando CSV de stock en Docker..."
	@test -n "$(CSV)" || (echo "Falta CSV. Uso: make import CSV=ruta/archivo.csv" && exit 1)
	$(COMPOSE) exec $(SERVICE) $(MANAGE) import_mamiru_stock "$(CSV)"
	@echo "Importacion lista. Revisa productos: $(PRODUCTS_ADMIN_URL)"

seed: ## Importar stock inicial. Uso: make seed SEED_FILE=data/stock.csv
	@echo "Importando stock inicial desde $(SEED_FILE)..."
	$(COMPOSE) exec $(SERVICE) $(MANAGE) import_mamiru_stock "$(SEED_FILE)" --skip-existing --seed-codes
	@echo "Seed aplicado. Productos: $(PRODUCTS_ADMIN_URL)"

reset-db: ## Resetear la base local de Docker sin borrar media
	@echo "Reseteando base local de Docker..."
	@echo "Esto borra el volumen Docker: $(DB_VOLUME)"
	$(COMPOSE) down --remove-orphans
	docker volume rm $(DB_VOLUME)
	$(COMPOSE) up --build -d
	@echo "Base reiniciada y servicios arriba."
	@echo "Siguiente paso habitual: make migrate && make seed && make superuser"
	@echo "Admin: $(ADMIN_URL)"

$(VENV_STAMP): requirements.txt
	@echo "Creando entorno virtual local en $(VENV)..."
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install -r requirements.txt
	@touch $(VENV_STAMP)

venv: $(VENV_STAMP) ## Crear entorno virtual local e instalar dependencias
	@echo "Entorno virtual listo: $(VENV)"

runserver: env venv ## Levantar servidor local usando Postgres de make up
	@echo "Levantando servidor local con Django..."
	@echo "  Dirección:     http://$(RUNSERVER_ADDR)/"
	@echo "  Base de datos: $(LOCAL_DATABASE_URL)"
	@echo "Aplicando migraciones en Postgres local..."
	DATABASE_URL=$(LOCAL_DATABASE_URL) $(LOCAL_MANAGE) migrate --noinput
	@echo "Preparando archivos estáticos locales..."
	DATABASE_URL=$(LOCAL_DATABASE_URL) STATIC_ROOT=$(LOCAL_STATIC_ROOT) $(LOCAL_MANAGE) collectstatic --noinput
	DATABASE_URL=$(LOCAL_DATABASE_URL) STATIC_ROOT=$(LOCAL_STATIC_ROOT) $(LOCAL_MANAGE) runserver $(RUNSERVER_ADDR)

sqlite-runserver: env venv ## Levantar servidor local con SQLite temporal
	@echo "Levantando servidor local con Django y SQLite temporal..."
	@echo "  Dirección:     http://$(RUNSERVER_ADDR)/"
	@echo "Aplicando migraciones en SQLite temporal..."
	DATABASE_URL=$(SQLITE_DATABASE_URL) $(LOCAL_MANAGE) migrate --noinput
	@echo "Preparando archivos estáticos locales..."
	DATABASE_URL=$(SQLITE_DATABASE_URL) STATIC_ROOT=$(LOCAL_STATIC_ROOT) $(LOCAL_MANAGE) collectstatic --noinput
	DATABASE_URL=$(SQLITE_DATABASE_URL) STATIC_ROOT=$(LOCAL_STATIC_ROOT) $(LOCAL_MANAGE) runserver $(RUNSERVER_ADDR)

local-run: env venv ## Levantar servidor local respetando DATABASE_URL de .env
	@echo "Levantando servidor de desarrollo local..."
	@echo "  Dirección:     http://$(RUNSERVER_ADDR)/"
	$(LOCAL_MANAGE) runserver $(RUNSERVER_ADDR)

local-migrate: env venv ## Ejecutar migraciones localmente
	@echo "Ejecutando migraciones localmente..."
	$(LOCAL_MANAGE) migrate
	@echo "Migraciones locales aplicadas. Admin: $(ADMIN_URL)"

local-makemigrations: env venv ## Crear migraciones localmente
	@echo "Creando migraciones localmente..."
	$(LOCAL_MANAGE) makemigrations
	@echo "Migraciones locales creadas. Revisalas con: git diff catalog/migrations"

local-superuser: env venv ## Crear superusuario localmente
	@echo "Creando superusuario localmente..."
	$(LOCAL_MANAGE) createsuperuser
	@echo "Cuando termines, entra al admin: $(ADMIN_URL)"

local-test: venv ## Ejecutar tests localmente con SQLite temporal
	@echo "Ejecutando tests localmente..."
	DATABASE_URL=$(SQLITE_DATABASE_URL) $(LOCAL_MANAGE) test
	@echo "Tests locales OK."

local-shell: env venv ## Abrir shell de Django localmente
	@echo "Abriendo shell de Django localmente..."
	@echo "Modelo util: from catalog.models import Product, PurchaseOrder"
	$(LOCAL_MANAGE) shell

lint: venv ## Ejecutar ruff check localmente
	@echo "Ejecutando ruff check..."
	$(LOCAL_RUFF) check . --no-cache
	@echo "Ruff check OK."

format: venv ## Ejecutar ruff format localmente
	@echo "Ejecutando ruff format..."
	$(LOCAL_RUFF) format .
	@echo "Formato aplicado."

lint-fix: venv ## Ejecutar ruff check con autofix localmente
	@echo "Ejecutando ruff check --fix..."
	$(LOCAL_RUFF) check . --fix --no-cache
	@echo "Autofix aplicado. Revisa el diff antes de commitear."

pytest: venv ## Ejecutar tests con pytest localmente
	@echo "Ejecutando pytest..."
	DATABASE_URL=$(SQLITE_DATABASE_URL) $(LOCAL_PYTEST)
	@echo "Pytest OK."

pytest-cov: pytest ## Alias de pytest, que ya corre coverage por pyproject.toml
